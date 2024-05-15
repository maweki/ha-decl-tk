import ast

from logging import Logger, getLogger
logger = getLogger(__package__)

def negate(node):
  return ast.UnaryOp(ast.Not(), node)

def code_to_ast(code):
  parsed = ast.parse(code)
  invariant = parsed.body[0]
  return invariant

# to negation normal form:
# [X]: apply a o b o c -> a o b and b o c
# [X]: apply b if a else c -> a and b or ~a and c
# [X]: expand a in b to a == eval(b)[0] or ...or a == eval(b)[n] and
# [X]: apply a is not b -> not (a is b)
# [X]: apply a is b -> (a or not b) and (not a or b)
# [X]: move nots inwards with de morgan
# [X]: remove double negation -> https://en.wikipedia.org/wiki/Negation_normal_form
# [X] Distribute ORs inwards over ANDs: a or (b and c) -> (a or b) and (b or c) | to conjunctive normal form
# [ ]: error on disallowed functions

def val_to_ast(val):
  return ast.Constant(val)

def _generic_visit(self, node):
  if isinstance(node, ast.UnaryOp):
    return ast.UnaryOp(node.op, self.visit(node.operand))
  elif isinstance(node, ast.Constant):
    return node
  elif isinstance(node, ast.Expr):
    return self.visit(node.value)
  elif isinstance(node, ast.BoolOp):
    return ast.BoolOp(node.op, [self.visit(v) for v in node.values])
  elif isinstance(node, ast.Compare):
    return ast.Compare(self.visit(node.left), node.ops, [self.visit(v) for v in node.comparators])
  elif isinstance(node, ast.IfExp):
    return ast.IfExp(self.visit(node.test), self.visit(node.body), self.visit(node.orelse))
  elif isinstance(node, ast.Call):
    return node
  elif isinstance(node, ast.List):
    return node
  elif isinstance(node, ast.Name):
    raise NotImplementedError("Bare names are not allowed:", node.id)
  raise NotImplementedError(node)

class ifelse_expander(ast.NodeTransformer):
  generic_visit = _generic_visit
  def visit_IfExp(self, node):
    positive = ast.BoolOp(ast.And(), [node.test, node.body])
    negative = ast.BoolOp(ast.And(), [negate(node.test), node.orelse])
    return self.visit(ast.BoolOp(ast.Or(), [positive, negative]))

class multicomp_expander(ast.NodeTransformer):
  generic_visit = _generic_visit
  def visit_Compare(self, node):
    left = ast.Compare(self.visit(node.left), [node.ops[0]], [self.visit(node.comparators[0])])
    if len(node.ops) > 1:
      right = self.visit(ast.Compare(node.comparators[0], node.ops[1:], node.comparators[1:]))
      new_node = ast.BoolOp(ast.And(), [left, right])
      return new_node
    else:
      return left

class isnot_to_not_is_visitor(ast.NodeTransformer):
  generic_visit = _generic_visit
  def visit_Compare(self, node):
    assert len(node.ops) == 1
    if isinstance(node.ops[0], ast.IsNot):
      return negate(ast.Compare(self.visit(node.left), [ast.Is()], [self.visit(node.comparators[0])]))
    else:
      return ast.Compare(self.visit(node.left), [node.ops[0]], [self.visit(node.comparators[0])])

class in_expand(ast.NodeTransformer):
  generic_visit = _generic_visit
  def visit_Compare(self, node):
    assert len(node.ops) == 1
    if isinstance(node.ops[0], ast.In):
      right = ast.literal_eval(node.comparators[0])
      if len(right) == 0:
        return val_to_ast(False)
      else:
        comps = [ast.Compare(self.visit(node.left), [ast.Eq()], [val_to_ast(v)]) for v in right]
        return ast.BoolOp(ast.Or(), comps)
    elif isinstance(node.ops[0], ast.NotIn):
      right = ast.literal_eval(node.comparators[0])
      if len(right) == 0:
        return val_to_ast(True)
      else:
        comps = [ast.Compare(self.visit(node.left), [ast.NotEq()], [val_to_ast(v)]) for v in right]
        return ast.BoolOp(ast.And(), comps)
    else:
      return ast.Compare(self.visit(node.left), [node.ops[0]], [self.visit(node.comparators[0])])

def rewrite_equiv(left, right):
  return ast.BoolOp(ast.And(), [ast.BoolOp(ast.Or(), [negate(left), right]), ast.BoolOp(ast.Or(), [left, negate(right)])])

class convert_equivalence(ast.NodeTransformer):
  generic_visit = _generic_visit
  def visit_Compare(self, node):
    assert len(node.ops) == 1
    if isinstance(node.ops[0], ast.Is):
      left = self.visit(node.left)
      right = self.visit(node.comparators[0])
      return rewrite_equiv(left, right)
    else:
      return ast.Compare(self.visit(node.left), [node.ops[0]], [self.visit(node.comparators[0])])

class move_negations(ast.NodeTransformer):
  generic_visit = _generic_visit
  def visit_UnaryOp(self, node):
    if not isinstance(node.op, ast.Not):
      return self.visit(node)
    n = node.operand
    if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.Not):
      return self.visit(n.operand)
    if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or):
      return ast.BoolOp(ast.And(), [self.visit(negate(v)) for v in n.values])
    if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.And):
      return ast.BoolOp(ast.Or(), [self.visit(negate(v)) for v in n.values])
    if isinstance(n, ast.Compare):
      assert len(n.ops) == 1
      op = n.ops[0]
      right = n.comparators[0]
      left = n.left
      mapping = [(ast.Eq, ast.NotEq), (ast.Lt, ast.GtE), (ast.Gt, ast.LtE)]
      for old, new in mapping + [(r, l) for (l, r) in mapping]:
        if isinstance(op, old):
          return self.visit(ast.Compare(left, [new()], [right]))
    return node

class distribute(ast.NodeTransformer):
  generic_visit = _generic_visit
  def visit_BoolOp(self, node):
    if isinstance(node.op, ast.And):
      for idx, v in enumerate(node.values):
        if isinstance(v, ast.BoolOp) and isinstance(v.op, ast.And):
          return self.visit(ast.BoolOp(ast.And(), node.values[0:idx] + v.values + node.values[idx+1:]))
    if isinstance(node.op, ast.Or):
      for idx, v in enumerate(node.values):
        if isinstance(v, ast.BoolOp) and isinstance(v.op, ast.Or):
          return self.visit(ast.BoolOp(ast.Or(), node.values[0:idx] + v.values + node.values[idx+1:]))
        if isinstance(v, ast.BoolOp) and isinstance(v.op, ast.And):
          return self.visit(ast.BoolOp(ast.And(), [ ast.BoolOp(ast.Or(), [a] + node.values[0:idx] + node.values[idx+1:]) for a in v.values]))
    return self.generic_visit(node)

from itertools import product
class simplify(ast.NodeTransformer):
  generic_visit = _generic_visit
  def visit_BoolOp(self, node):
    if isinstance(node.op, ast.And):
      new_values = [self.visit(v) for v in node.values if ast.unparse(v) != ast.unparse(ast.Constant(True))]
      if len(new_values) == 0:
        return ast.Constant(True)
      if len(new_values) == 1:
        return new_values[0]
      return ast.BoolOp(ast.And(), new_values)
    if isinstance(node.op, ast.Or):
      vs = node.values
      for v in vs:
        if ast.unparse(v) == ast.unparse(ast.Constant(True)):
          return ast.Constant(True)
      for i1, i2 in product(range(len(vs)), repeat=2):
        if isinstance(vs[i1], ast.UnaryOp) and isinstance(vs[i1].op, ast.Not) and ast.unparse(vs[i2]) == ast.unparse(vs[i1].operand):
          return ast.Constant(True)
    return self.generic_visit(node)

# allowed functions:
#   * is_state(entity, val):bool
#   * states(entity): val
#   * is_state_attr(entity, attr, val):bool
#   * state_attr(entity, attr):val
#   * has_value(entity):bool

class check_functions(ast.NodeTransformer):
  generic_visit = _generic_visit
  allowed_funcs = ['is_state', 'states', 'is_state_attr', 'state_attr', 'has_value']
  def visit_Call(self, node):
    if not isinstance(node.func, ast.Name):
      raise ValueError("Only " + str(self.allowed_funcs) + " are allowed functions")
    elif node.func.id not in self.allowed_funcs:
      raise ValueError("Function name " + str(node.func.id) + " not in allowed functions " + str(self.allowed_funcs))
    return node

#####################################################


pipeline = [ multicomp_expander
           , ifelse_expander
           , in_expand
           , isnot_to_not_is_visitor
           , convert_equivalence
           , move_negations
           , distribute
           , distribute
           , simplify
           , simplify
           , check_functions
           ]

def code_to_cnf(code):
  node = code_to_ast(code)
  for f in pipeline:
    node = f().visit(node)
  return node

def eval_cnf(hass, node):
  class eval_visitor(ast.NodeVisitor):

    def generic_visit(self, node):
      raise NotImplementedError(node)

    def visit_BoolOp(self, node):
      if isinstance(node.op, ast.Or):
        return any(self.visit(n) for n in node.values)
      if isinstance(node.op, ast.And):
        return all(self.visit(n) for n in node.values)

    def visit_UnaryOp(self, node):
      if not isinstance(node.op, ast.Not):
        raise NotImplementedError(node.op)
      else:
        return not self.visit(node.operand)

    def visit_Call(self, node):
      if node.func.id == 'is_state':
        entity, state = node.args
        # logger.debug("is_state(" + entity.value + ', ' + state.value + ') == ' + hass.states.get(entity.value).state)
        return hass.states.get(entity.value).state == state.value
      if node.func.id == 'states':
        entity, = node.args
        return hass.states.get(entity.value).state
      raise NotImplementedError(node)

    def visit_Compare(self, node):
      left = node.left
      right = node.comparators[0]
      comp = node.ops[0]

      import operator
      for (optype, opfunc) in [(ast.Lt ,operator.lt),(ast.LtE ,operator.le),(ast.Eq ,operator.eq),(ast.NotEq ,operator.ne),(ast.GtE ,operator.ge),(ast.Gt ,operator.gt),]:
        if isinstance(comp, optype):
          return opfunc(self.visit(left), self.visit(right))
      raise NotImplementedError(node)
  return eval_visitor().visit(node)


def get_used_entities(node):
  entities = []
  class entity_gatherer(ast.NodeVisitor):
    generic_visit = _generic_visit
    def visit_Call(self, node):
      ename = node.args[0]
      assert isinstance(ename, ast.Constant)
      entities.append(ename.value)
  entity_gatherer().visit(node)
  return frozenset(entities)

def _fresh_variables():
  i = 0
  while True:
    yield 'V' + str(i)
    i += 1
fresh_variables = iter(_fresh_variables())
fresh_variable = lambda : ast.Name(next(fresh_variables), ast.Load())

def split_disjunctions(node):
  if isinstance(node, ast.BoolOp) and isinstance(node.op, ast.And):
    return node.values
  return [node]

# gives the body for false :- body
def to_implication_form(node):
  return move_negations().visit(negate(node))

def create_literal(node):
  if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
    return "not " + create_literal(node.operand)
  if isinstance(node, ast.Call):
    if node.func.id == 'states':
      node.func.id = 'is_state'
    if node.func.id == 'is_state':
      assert len(node.args) == 2
    if node.func.id == 'state_attr':
      node.func.id = 'is_state_attr'
    if node.func.id == 'is_state_attr':
      assert len(node.args) == 3
    if node.func.id == 'has_value':
      assert len(node.args) == 1
    return ast.unparse(ast.Call(node.func, auto_round_constant_list(node.args), []))
  if isinstance(node, ast.Compare):
    # check that these are the states/state_attr function
    left = node.left
    op = node.ops[0]
    right = node.comparators[0]
    subbody = []
    if isinstance(left, ast.Call) and isinstance(right, ast.Call):
      lvar = fresh_variable()
      rvar = fresh_variable()
      subbody.append(ast.Call(left.func, auto_round_constant_list(left.args) + [lvar], []))
      subbody.append(ast.Call(right.func, auto_round_constant_list(right.args) + [rvar], []))
      subbody.append(ast.Compare(lvar, [op], [rvar]))
      return ', '.join(create_literal(s) for s in subbody)
    if isinstance(left, ast.Call) and isinstance(right, (ast.Expr,ast.Constant)):
      lvar = fresh_variable()
      rvar = auto_round_constant(right)
      subbody.append(ast.Call(left.func, auto_round_constant_list(left.args) + [lvar],[]))
      subbody.append(ast.Compare(lvar, [op], [rvar]))
      return ', '.join(create_literal(s) for s in subbody)
  return ast.unparse(node)

def implication_body_to_rule(body):
  if isinstance(body, ast.BoolOp) and isinstance(body.op, ast.And):
    return ":- " + ', '.join(create_literal(b) for b in body.values) + '.'
  if isinstance(body, (ast.UnaryOp, ast.Call, ast.Compare)):
    return ":- " + create_literal(body) + '.'
  raise NotImplementedError(body)

def auto_round(value):
  try:
    return round(float(value))
  except:
    return str(value)
def auto_round_constant(node):
  if isinstance(node, ast.Constant):
    return ast.Constant(auto_round(node.value))
  return node
auto_round_constant_list = lambda l: [auto_round_constant(c) for c in l]

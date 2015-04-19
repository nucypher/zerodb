from repoze.catalog import query


Query = query.Query
Comparator = query.Comparator
Contains = query.Contains
DoesNotContain = query.DoesNotContain
Eq = query.Eq
NotEq = query.NotEq

# Queries to pass catalog
Gt = query.Gt
Lt = query.Lt
Ge = query.Ge
Le = query.Le
InRange = query.InRange
NotInRange = query.NotInRange

Any = query.Any
NotAny = query.NotAny
All = query.All
NotAll = query.NotAll

# Query to replace tree family
BoolOp = query.BoolOp
Not = query.Not

Name = query.Name

optimize = query.optimize
parse_query = query.parse_query

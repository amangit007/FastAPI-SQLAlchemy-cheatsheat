## Third highest salary
```python
query = (
    select(Employee.name, Employee.salary)
    .order_by(Employee.salary.desc())
    .limit(3)
    .offset(2)
)
```


## Ascending and descending order in sqlalchemy
```python
query = select(Item).order_by(Item.name.desc())
```


## Use of  AND OR NOT clauses in sqlalchemy filter query
```python
data = db.query(Item).filter(or_(not_(Item.is_active), Item.name == "test"))
```

## Chaining of steps in sqlalchemy
```python
query = select(Item).all()
if age:
    query = query.where(Item.age == age)
if name:
    query = query.where(Item.name == name)
```




## Use of having clause

```python
query = (
    select(Employee.name, Employee.salary)
    .group_by(Employee.name)
    .having(func.count(Employee.name) > 1)
)
```







## SQL Text Query with parameters

```python
query = text("SELECT * FROM items WHERE name = :name")
result = db.execute(query, {"name": "John"})
print(result.fetchall())
```

## SQLAlchemy code to query table with left joins and aggregation

```python
from sqlalchemy import select, func, case

query = (
    select(
        Request.id.label("request_id"),
        Request.created_by.label("request_created_by"),
        Request.requester_name.label("requester_name"),
        func.coalesce(
            func.json_agg(
                case(
                    (Training.id.is_not(None),
                     func.json_build_object(
                        'request_training_junction_id', RequestTrainingJunction.id,
                        'training_id', Training.id,
                        'training_name', Training.name
                     ))
                )
            ).filter(Training.id.is_not(None)),  # Remove NULL entries from array
            '[]'  # Return empty array instead of [null]
        ).label("trainings")
    )
    .outerjoin(RequestTrainingJunction, Request.id == RequestTrainingJunction.request_id)
    .join(Training, RequestTrainingJunction.training_id == Training.id)
    .where(Request.is_active == True)
    .group_by(Request.id, Request.created_by, Request.requester_name)
)
```



## SQLAlchemy code to query table with inner joins only and aggregation


```python
query = (
    select(
        Request.id.label("request_id"),
        Request.created_by.label("request_created_by"),
        Request.requester_name.label("requester_name"),
        func.coalesce(
            func.json_agg(
                func.json_build_object(
                    'request_training_junction_id', RequestTrainingJunction.id,
                    'training_id', Training.id,
                    'training_name', Training.name
                )
            ),
            '[]'
        ).label("trainings")
    )
    .join(RequestTrainingJunction, Request.id == RequestTrainingJunction.request_id)
    .join(Training, RequestTrainingJunction.training_id == Training.id)
    .where(Request.is_active == True)
    .group_by(Request.id, Request.created_by, Request.requester_name)
)
```






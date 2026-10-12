"""Fake in-memory data, just so the demo endpoints have something to return."""

APP_USERS = [
    {"id": 1, "username": "alice", "email": "alice@example.com", "role": "admin"},
    {"id": 2, "username": "bob", "email": "bob@example.com", "role": "manager"},
    {"id": 3, "username": "carol", "email": "carol@example.com", "role": "user"},
]

DEPARTMENTS = [
    {"id": 1, "code": "ENG", "name": "Engineering", "cost_center": "CC-100"},
    {"id": 2, "code": "SAL", "name": "Sales", "cost_center": "CC-200"},
    {"id": 3, "code": "FIN", "name": "Finance", "cost_center": "CC-300"},
]

STATUSES = [
    {"id": 1, "code": "OPEN", "label": "Open"},
    {"id": 2, "code": "IN_PROGRESS", "label": "In Progress"},
    {"id": 3, "code": "CLOSED", "label": "Closed"},
]

REPORTS = [
    {"id": 1, "title": "Q1 Revenue", "department_id": 2, "status_id": 3, "amount": 125000},
    {"id": 2, "title": "Headcount Plan", "department_id": 1, "status_id": 2, "amount": None},
    {"id": 3, "title": "Audit Findings", "department_id": 3, "status_id": 1, "amount": 8200},
]

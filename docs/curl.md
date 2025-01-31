# Useful curl commands

## Clickable objects

### Add clickable icon
```shell
curl -X POST "http://localhost:8000/send-to-overlay" \
     -H "Content-Type: application/json" \
     -d '{ "clickable": {
            "action": "add",
            "object_id": "star-icon",
            "x": 300,
            "y": 400,
            "width": 60,
            "height": 60,
            "iconClass": "fa-star"
        }
    }'
```

### Add clickable HTML
```shell
curl -X POST "http://localhost:8000/send-to-overlay" \
     -H "Content-Type: application/json" \
     -d '{ "clickable": {
            "action": "add",
            "object_id": "html-test",
            "x": 400,
            "y": 600,
            "width": 300,
            "height": 60,
            "html": "Ich bin ein Test!"
        }
    }'
```

### Get all clickable objects
```shell
curl -X GET "http://localhost:8000/get-clickable-objects"
```

### Remove clickable object
```shell
curl -X DELETE "http://localhost:8000/remove-clickable-object?object_id=star-icon"
```

## HTML objects
```shell
curl -X POST http://localhost:8000/send-to-overlay -H "Content-Type: application/json" -d '{"html": { "content": "<div style=\"background-color: red; width: 40px; height: 40px; position: absolut; top: 700px; left: 300px;\">TEST</div>", "lifetime": 10000 } }'
```

## Icons

### Add icon
```shell
curl -X POST http://localhost:8000/send-to-overlay -H "Content-Type: application/json" -d '{"icon": { "id": "test1", "action": "add", "name": "fa-print" } }'
```

### Remove icon
```shell
curl -X POST http://localhost:8000/send-to-overlay -H "Content-Type: application/json" -d '{"icon": { "id": "test1", "action": "remove", "name": "fa-print" } }'
```

## Alerts
```shell
curl -X POST http://localhost:8000/send-to-overlay -H "Content-Type: application/json" -d '{"alert": { "type": "follower", "user": "Ferdyverse" } }'

curl -X POST http://localhost:8000/send-to-overlay -H "Content-Type: application/json" -d '{"alert": { "type": "subscriber", "user": "Ferdyverse" } }'

curl -X POST http://localhost:8000/send-to-overlay -H "Content-Type: application/json" -d '{"alert": { "type": "raid", "user": "Ferdyverse", "size": 20 } }'
```

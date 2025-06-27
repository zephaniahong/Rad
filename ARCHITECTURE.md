```
+----------------+          +--------------------+          +---------------------+
| CalDAV CalSync | <------> | Your FastAPI App   | <------> | Your Radicale Server|
|    Endpoint    |          | (Sync Service)     |          |   (CalDAV SSOT)     |
+----------------+          +--------------------+          +---------------------+
                                     ^
                                     |
                                     |
                                     v
                           +----------------------+
                           | Google Calendar      |
                           |  (via REST API /     |
                           |   Push Notifications)|
                           +----------------------+
```
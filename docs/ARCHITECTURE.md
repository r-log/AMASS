# Electrician Log MVP — Architecture Reference

**Audience:** Architecture Engineer Review
**Date:** 2026-04-14
**Stack:** Flask + Flask-Sock (Python) · Vue 3 + OpenSeadragon (JS) · SQLite · IndexedDB

This document presents the architecture as a series of Mermaid diagrams, organized from high-level context down to specific subsystem flows. Each diagram is self-contained and can be rendered in any Mermaid-compatible viewer (GitHub, VS Code, mermaid.live).

---

## 1. System Context (C4 Level 1)

High-level view of actors, the system, and external dependencies.

```mermaid
graph TB
    subgraph Users["👥 Users"]
        Worker["Electrician<br/>(role: worker)"]
        Supervisor["Site Supervisor<br/>(role: supervisor)"]
        Admin["System Admin<br/>(role: admin)"]
    end

    subgraph System["⚡ Electrician Log MVP"]
        WebApp["Frontend SPA<br/>Vue 3 + OpenSeadragon"]
        API["Backend API<br/>Flask + Flask-Sock"]
        DB[("SQLite Database")]
        FS[("File Storage<br/>floor-plans/ · tiles/<br/>project-backups/")]
    end

    subgraph External["External Tooling"]
        PDF["PyMuPDF<br/>(PDF rendering)"]
        Vips["pyvips / Pillow<br/>(tile generation)"]
    end

    Worker -->|"HTTPS / WSS"| WebApp
    Supervisor -->|"HTTPS / WSS"| WebApp
    Admin -->|"HTTPS / WSS"| WebApp

    WebApp <-->|"REST + WebSocket"| API
    API --> DB
    API --> FS
    API -.uses.-> PDF
    API -.uses.-> Vips

    classDef user fill:#E3F2FD,stroke:#1565C0,color:#000
    classDef sys fill:#FFF3E0,stroke:#E65100,color:#000
    classDef ext fill:#F3E5F5,stroke:#6A1B9A,color:#000
    class Worker,Supervisor,Admin user
    class WebApp,API,DB,FS sys
    class PDF,Vips ext
```

---

## 2. Container / Layered Architecture (C4 Level 2)

Internal containers, request paths, and persistence layers.

```mermaid
graph LR
    subgraph Browser["Browser Runtime"]
        direction TB
        UI["Vue 3 Views<br/>+ OpenSeadragon Map"]
        APIClient["core/api/<br/>API Services"]
        WSClient["core/realtime/<br/>ws-client.js"]
        OffQ["core/offline/<br/>offline-queue.js"]
        SW["sw-offline-sync.js<br/>(Service Worker)"]
        IDB[("IndexedDB<br/>offline_queue +<br/>offline_queue_blobs")]
    end

    subgraph Server["Flask Application"]
        direction TB
        Routes["app/api/<br/>Blueprints"]
        Mid["app/middleware/<br/>Rate Limiting"]
        Dec["app/utils/decorators<br/>JWT + RBAC"]
        Svc["app/services/<br/>Business Logic"]
        Models["app/models/<br/>Domain Entities"]
        RT["app/realtime/<br/>WS Hub"]
        DBLayer["app/database/<br/>connection.py"]
    end

    SQL[("SQLite")]
    Disk[("Local FS<br/>floor-plans · tiles<br/>backups")]

    UI --> APIClient
    UI --> WSClient
    APIClient --> OffQ
    OffQ <--> IDB
    OffQ -->|"online"| Routes
    SW -.replay on sync.-> Routes

    WSClient <-->|"WSS /ws?token="| RT

    Routes --> Mid
    Routes --> Dec
    Routes --> Svc
    Svc --> Models
    Svc --> RT
    Models --> DBLayer
    DBLayer --> SQL
    Svc --> Disk

    classDef front fill:#E8F5E9,stroke:#2E7D32,color:#000
    classDef back fill:#FFF8E1,stroke:#F9A825,color:#000
    classDef store fill:#ECEFF1,stroke:#37474F,color:#000
    class UI,APIClient,WSClient,OffQ,SW front
    class Routes,Mid,Dec,Svc,Models,RT,DBLayer back
    class IDB,SQL,Disk store
```

---

## 3. Backend Module Map

The Clean-Architecture style separation: **Routes → Services → Models → DB**.

```mermaid
graph TB
    subgraph API["app/api/ (HTTP Boundary)"]
        AAuth["auth/routes.py"]
        AProj["projects/routes.py"]
        AFloor["floors/routes.py"]
        AWL["work_logs/routes.py"]
        ACS["critical_sectors/routes.py"]
        AAsg["assignments/routes.py"]
        ATile["tiles/routes.py"]
        ADash["dashboard/routes.py"]
        ANotif["notifications/routes.py"]
    end

    subgraph SVC["app/services/ (Business Logic)"]
        SAuth["auth_service"]
        SProj["project_service"]
        SFloor["floor_service"]
        SWL["work_log_service"]
        SCS["critical_sector_service"]
        SAsg["assignment_service"]
        STile["tile_service"]
        SDash["dashboard_service"]
        SNotif["notification_service"]
        SBackup["project_backup_service"]
    end

    subgraph MOD["app/models/ (Entities)"]
        MUser["User"]
        MProject["Project"]
        MFloor["Floor"]
        MWL["WorkLog"]
        MCS["CriticalSector"]
        MAsg["Assignment"]
        MNotif["Notification"]
        MPUA["ProjectUserAssignment"]
        MCable["CableRoute"]
        MTpl["WorkTemplate"]
    end

    subgraph SUP["Supporting Layers"]
        RT["realtime/<br/>WebSocket Hub"]
        DEC["utils/decorators<br/>@token_required<br/>@role_required"]
        DB["database/connection.py<br/>migrations.py"]
        TG["utils/tile_generator_safe<br/>SafeTileGenerator"]
    end

    AAuth --> SAuth
    AProj --> SProj
    AFloor --> SFloor
    AWL --> SWL
    ACS --> SCS
    AAsg --> SAsg
    ATile --> STile
    ADash --> SDash
    ANotif --> SNotif

    SAuth --> MUser
    SProj --> MProject & SBackup
    SFloor --> MFloor
    SWL --> MWL & MCS
    SCS --> MCS
    SAsg --> MAsg & MWL
    SDash --> MWL & MAsg
    SNotif --> MNotif

    SWL -.broadcast.-> RT
    SAsg -.broadcast.-> RT
    SNotif -.broadcast.-> RT

    STile --> TG
    MUser & MProject & MFloor & MWL & MCS & MAsg & MNotif & MPUA & MCable & MTpl --> DB
    API --> DEC

    classDef api fill:#E1F5FE,stroke:#01579B,color:#000
    classDef svc fill:#FFF3E0,stroke:#E65100,color:#000
    classDef mod fill:#F1F8E9,stroke:#33691E,color:#000
    classDef sup fill:#FCE4EC,stroke:#880E4F,color:#000
    class AAuth,AProj,AFloor,AWL,ACS,AAsg,ATile,ADash,ANotif api
    class SAuth,SProj,SFloor,SWL,SCS,SAsg,STile,SDash,SNotif,SBackup svc
    class MUser,MProject,MFloor,MWL,MCS,MAsg,MNotif,MPUA,MCable,MTpl mod
    class RT,DEC,DB,TG sup
```

---

## 4. Frontend Module Map

```mermaid
graph TB
    subgraph Entry["Entry / Views"]
        Main["index.html / login.html"]
        OSDApp["app-openseadragon.js<br/>(Map View)"]
        Dash["dashboard.html<br/>+ dashboard-components.js"]
    end

    subgraph Core["frontend/core/"]
        subgraph CoreAPI["api/"]
            Client["api.client.js<br/>(base HTTP + Bearer)"]
            SAuth["auth.service"]
            SProj["projects.service"]
            SFloor["floors.service"]
            SWL["work_logs.service"]
            SCS["critical_sectors.service"]
            SAsg["assignments.service"]
            STile["tiles.service"]
            SDash["dashboard.service"]
            SNotif["notifications.service"]
        end
        WS["realtime/<br/>ws-client.js"]
        OffQ["offline/<br/>offline-queue.js"]
    end

    subgraph Map["frontend/map/"]
        MM["marker-manager.js"]
        CSDraw["critical-sector-drawer.js"]
    end

    subgraph SW["Service Worker"]
        SWFile["sw-offline-sync.js"]
    end

    IDB[("IndexedDB")]
    AuthMgr["auth.js<br/>(token storage)"]

    Main --> OSDApp
    Main --> Dash
    OSDApp --> MM & CSDraw
    OSDApp --> WS

    SAuth & SProj & SFloor & SWL & SCS & SAsg & STile & SDash & SNotif --> Client
    Client --> OffQ
    Client --> AuthMgr
    OffQ <--> IDB
    SWFile <--> IDB
    WS --> AuthMgr

    OSDApp --> SFloor & SWL & SCS & STile

    classDef entry fill:#E8EAF6,stroke:#283593,color:#000
    classDef core fill:#E0F2F1,stroke:#00695C,color:#000
    classDef map fill:#FFF9C4,stroke:#F57F17,color:#000
    classDef sw fill:#FFEBEE,stroke:#B71C1C,color:#000
    class Main,OSDApp,Dash entry
    class Client,SAuth,SProj,SFloor,SWL,SCS,SAsg,STile,SDash,SNotif,WS,OffQ core
    class MM,CSDraw map
    class SWFile sw
```

---

## 5. Domain Model (Entity-Relationship)

```mermaid
erDiagram
    USER ||--o{ PROJECT_USER_ASSIGNMENT : "has roles in"
    PROJECT ||--o{ PROJECT_USER_ASSIGNMENT : "assigns users"
    USER ||--o{ WORK_LOG : "authors (worker_id)"
    USER ||--o{ ASSIGNMENT : "assigned_to"
    USER ||--o{ ASSIGNMENT : "assigned_by"
    USER ||--o{ NOTIFICATION : "receives"

    PROJECT ||--o{ FLOOR : "contains"
    FLOOR ||--o{ WORK_LOG : "located on"
    FLOOR ||--o{ CRITICAL_SECTOR : "contains zones"
    FLOOR ||--o{ CABLE_ROUTE : "contains routes"

    WORK_LOG ||--o{ ASSIGNMENT : "tasked via"

    USER {
        int id PK
        string username UK
        string password_hash
        string full_name
        string role "admin|supervisor|worker"
        bool is_active
        datetime last_login
        datetime created_at
    }
    PROJECT {
        int id PK
        string name
        string description
        bool is_active
        int created_by FK
        datetime created_at
    }
    PROJECT_USER_ASSIGNMENT {
        int id PK
        int project_id FK
        int user_id FK
        string role
    }
    FLOOR {
        int id PK
        int project_id FK
        string name
        string image_path "PDF source"
        int width
        int height
        int sort_order
        bool is_active
    }
    WORK_LOG {
        int id PK
        int floor_id FK
        int worker_id FK
        float x_coord "0.0–1.0"
        float y_coord "0.0–1.0"
        string work_type
        string description
        string cable_type
        float cable_meters
        float start_x
        float start_y
        float end_x
        float end_y
        float hours_worked
        string status
        string priority
        datetime created_at
    }
    CRITICAL_SECTOR {
        int id PK
        int floor_id FK
        string sector_name
        float x_coord
        float y_coord
        float radius
        float width
        float height
        string sector_type "rectangle|circle|polygon"
        string priority
        bool is_active
        json points "polygon vertices"
    }
    ASSIGNMENT {
        int id PK
        int work_log_id FK
        int assigned_to FK
        int assigned_by FK
        date due_date
        string status "pending|accepted|completed|rejected"
        string notes
    }
    CABLE_ROUTE {
        int id PK
        int floor_id FK
        float start_x
        float start_y
        float end_x
        float end_y
        string cable_type
        float meters
    }
    NOTIFICATION {
        int id PK
        int user_id FK
        string message
        string event_type
        datetime read_at
    }
```

---

## 6. Authentication & Authorization Flow

```mermaid
sequenceDiagram
    actor U as User (Browser)
    participant FE as Frontend (auth.service)
    participant API as POST /api/auth/login
    participant SAuth as auth_service
    participant DB as SQLite
    participant Dec as @token_required<br/>@role_required
    participant Route as Protected Route

    U->>FE: submit credentials
    FE->>API: POST {username, password}
    API->>SAuth: authenticate(username, pw)
    SAuth->>DB: SELECT user WHERE username
    DB-->>SAuth: user row
    SAuth->>SAuth: bcrypt verify · check is_active
    SAuth->>SAuth: generate_token() → JWT<br/>{user_id, role, exp, iat}
    SAuth-->>API: ServiceResult(token, user)
    API-->>FE: 200 {token, user}
    FE->>FE: localStorage.setItem('token')

    Note over U,Route: Subsequent authenticated request

    U->>FE: action
    FE->>Route: GET/POST + Authorization: Bearer <jwt>
    Route->>Dec: enter decorator chain
    Dec->>Dec: extract_bearer_token()
    Dec->>SAuth: verify_token(jwt)
    SAuth->>SAuth: jwt.decode + blacklist check
    SAuth->>DB: confirm user.is_active
    DB-->>SAuth: ok
    SAuth-->>Dec: user_data
    Dec->>Dec: role in allowed_roles?
    alt authorized
        Dec->>Route: request.current_user = user
        Route-->>FE: 200 + payload
    else forbidden
        Dec-->>FE: 403 Forbidden
    else token invalid / expired / revoked
        Dec-->>FE: 401 Unauthorized
    end

    Note over U,SAuth: Logout adds JTI to in-memory _TokenBlacklist<br/>until token's exp timestamp
```

---

## 7. Realtime / WebSocket Hub

### 7a. Connection & Subscription

```mermaid
sequenceDiagram
    participant C as ws-client.js
    participant WS as Flask-Sock /ws
    participant Hub as realtime hub
    participant SAuth as auth_service

    C->>WS: connect(ws://.../ws?token=<jwt>)
    WS->>Hub: on_connect(ws)
    Hub->>Hub: _get_token() from query
    Hub->>SAuth: validate_token_middleware(token)
    SAuth-->>Hub: user_data | None

    alt valid token
        Hub->>Hub: register ws → {user:{id}, role:{role}}
        Hub-->>C: {type:'connected', rooms:[...]}
    else invalid
        Hub-->>C: {type:'error', message:'Unauthorized'}
        Hub->>WS: close()
    end

    C->>Hub: {type:'subscribe', rooms:['floor:5']}
    Hub->>Hub: validate room (own user/role/any floor)
    Hub-->>C: {type:'subscribed', rooms:['floor:5']}

    Note over C,Hub: Heartbeat: 300s timeout per client
```

### 7b. Broadcast Pattern

```mermaid
graph LR
    subgraph Server
        WLSvc["work_log_service<br/>.create()"]
        Hub["realtime hub<br/>broadcast(event, data, room)"]
        Reg[("_clients dict<br/>ws → set rooms")]
    end

    subgraph Clients
        W1["Worker A<br/>rooms: user:1, role:worker, floor:5"]
        W2["Worker B<br/>rooms: user:2, role:worker, floor:5"]
        S1["Supervisor<br/>rooms: user:9, role:supervisor"]
        A1["Admin<br/>rooms: user:1, role:admin"]
    end

    WLSvc -->|"work_log_created<br/>room='floor:5'"| Hub
    WLSvc -->|"stats_changed<br/>rooms=[role:supervisor,role:admin]"| Hub
    Hub --> Reg
    Reg -.->|"floor:5 ∋ ws"| W1
    Reg -.->|"floor:5 ∋ ws"| W2
    Reg -.->|"role:supervisor"| S1
    Reg -.->|"role:admin"| A1

    classDef server fill:#FFF3E0,stroke:#E65100,color:#000
    classDef client fill:#E8F5E9,stroke:#2E7D32,color:#000
    class WLSvc,Hub,Reg server
    class W1,W2,S1,A1 client
```

---

## 8. Offline-First Mutation Flow

### 8a. State Machine

```mermaid
stateDiagram-v2
    [*] --> Online
    Online --> Offline: navigator.onLine = false<br/>or fetch fails
    Offline --> Queueing: POST/PUT/DELETE issued
    Queueing --> Offline: entry stored in IndexedDB<br/>(metadata + blobs)
    Offline --> Reachable: poll /api/auth/verify OK
    Reachable --> Replaying: drain queue (ordered by createdAt)
    Replaying --> Replaying: success → delete entry
    Replaying --> Retry: failure (retryCount < 3)
    Retry --> Replaying: backoff
    Replaying --> Online: queue empty
    Online --> [*]

    note right of Queueing
        GET requests are NOT queued —
        they throw "offline" immediately.
    end note
    note right of Replaying
        Service Worker 'sync' event
        triggers same replay path
        when tab is closed.
    end note
```

### 8b. Sequence — Offline POST + Replay

```mermaid
sequenceDiagram
    participant App as Vue View
    participant Svc as work_logs.service
    participant OQ as OfflineQueue
    participant IDB as IndexedDB
    participant SW as Service Worker
    participant API as Backend

    Note over App,API: 🔴 Offline
    App->>Svc: createWorkLog(formData)
    Svc->>OQ: fetchFormData(url, {method:POST, body})
    OQ->>OQ: navigator.onLine? → false
    OQ->>IDB: serialize FormData<br/>blobs → STORE_BLOBS<br/>meta → offline_queue
    IDB-->>OQ: stored
    OQ-->>Svc: 202 Queued (synthetic Response)
    Svc-->>App: optimistic ok

    Note over App,API: 🟢 Network restored
    OQ->>API: GET /api/auth/verify (poll)
    API-->>OQ: 200 OK
    OQ->>IDB: read all queued entries (order: createdAt)
    IDB-->>OQ: entries[]
    loop for each entry
        OQ->>OQ: rebuild FormData from blobs
        OQ->>API: fetch(url, method, headers, body)
        alt success
            API-->>OQ: 200/201
            OQ->>IDB: delete entry + blobs
        else fail
            OQ->>IDB: increment retryCount
        end
    end

    Note over SW,IDB: SW also runs same replay<br/>via 'sync' event when tab is closed
```

---

## 9. Image Tile Generation Pipeline

```mermaid
flowchart LR
    A["📄 PDF<br/>floor-plans/floor.pdf"] --> B["PyMuPDF<br/>fitz.open()"]
    B --> C["Render @ 300 DPI<br/>page.get_pixmap()"]
    C --> D["PIL.Image (RGB)<br/>close PDF"]
    D --> E{"Calculate DZI levels<br/>levels = ⌈log2(max(W,H)/tile)⌉"}
    E --> F["Per-level loop"]
    F --> G["Downsample image"]
    G --> H["Slice into tiles<br/>256–512 px<br/>+1 px overlap"]
    H --> I["Encode tile<br/>WebP (default)<br/>· PNG · JPEG"]
    I --> J["Save tile<br/>floor-{id}_files/<br/>{level}/{x}_{y}.webp"]
    J --> K{"more levels?"}
    K -->|"yes"| F
    K -->|"no"| L["Write DZI XML<br/>floor-{id}.dzi"]
    L --> M["✅ Ready for OpenSeadragon"]

    F -.progress.-> P[("SafeTileGenerator._progress<br/>(thread-safe)")]
    P -.poll.-> FE["Frontend<br/>tiles.service.getStatus()"]

    classDef step fill:#E3F2FD,stroke:#0277BD,color:#000
    classDef io fill:#FFF8E1,stroke:#F9A825,color:#000
    classDef done fill:#C8E6C9,stroke:#1B5E20,color:#000
    class A,J,L io
    class B,C,D,E,F,G,H,I,K step
    class M done
```

**Memory safeguards:** `Image.MAX_IMAGE_PIXELS = 500M`, eager `gc.collect()` per level, PDF closed immediately after rasterization.

---

## 10. End-to-End Request Lifecycle (Worker Creates a Work Log)

The integration of all subsystems for a single representative action.

```mermaid
sequenceDiagram
    actor W as Worker
    participant OSD as OpenSeadragon
    participant View as work-log form
    participant Svc as work_logs.service
    participant OQ as OfflineQueue
    participant API as POST /api/work-logs
    participant Dec as @token_required
    participant WLS as work_log_service
    participant CSS as critical_sector_service
    participant DB as SQLite
    participant Hub as realtime hub
    participant FE2 as Other clients<br/>(floor:5 room)

    W->>OSD: click on floor plan (x, y)
    OSD->>OSD: convert pixel → normalized (0–1)
    OSD->>View: open form @ (x, y)
    W->>View: fill {work_type, description, ...}
    View->>Svc: createWorkLog(formData)
    Svc->>OQ: fetchFormData(POST /api/work-logs)

    alt online
        OQ->>API: HTTP POST + Bearer token
    else offline
        OQ->>OQ: queue → IndexedDB · return synthetic 202
        Note over OQ,API: replay later (see §8)
    end

    API->>Dec: auth + role check
    Dec->>API: ok (worker can create own)
    API->>WLS: create_work_log(user, data)
    WLS->>CSS: check overlap with critical sectors
    CSS->>DB: SELECT critical_sectors WHERE floor_id
    DB-->>CSS: sectors
    CSS-->>WLS: warnings (if any)
    WLS->>DB: INSERT work_log
    DB-->>WLS: id
    WLS->>Hub: broadcast('work_log_created', data, room='floor:5')
    WLS->>Hub: broadcast_to_rooms('stats_changed', {}, ['role:supervisor','role:admin'])
    WLS-->>API: ServiceResult(work_log)
    API-->>Svc: 201 + work_log

    Hub-->>FE2: push 'work_log_created'
    FE2->>FE2: marker-manager.add(...)
    FE2->>FE2: dashboard updates stats
```

---

## 11. Deployment View

```mermaid
graph TB
    subgraph Host["Server Host (Linux / Windows)"]
        subgraph Container["Docker Container (optional)"]
            Flask["Flask App<br/>python backend/run.py<br/>:5000"]
            Static["Static frontend/<br/>served by Flask"]
            Sock["Flask-Sock<br/>/ws endpoint"]
        end
        Vol1[("./floor-plans")]
        Vol2[("./tiles")]
        Vol3[("./project-backups")]
        Vol4[("./database.db")]
    end

    subgraph Edge["Reverse Proxy (recommended)"]
        Nginx["Nginx / Traefik<br/>TLS · WebSocket upgrade"]
    end

    Browser["Browser Client"] -->|"HTTPS :443"| Nginx
    Browser -->|"WSS :443"| Nginx
    Nginx -->|"HTTP :5000"| Flask
    Nginx -->|"WS :5000"| Sock

    Flask --- Vol1 & Vol2 & Vol3 & Vol4
    Static --- Flask
    Sock --- Flask

    classDef host fill:#FFF3E0,stroke:#E65100,color:#000
    classDef edge fill:#E1F5FE,stroke:#01579B,color:#000
    classDef vol fill:#ECEFF1,stroke:#37474F,color:#000
    class Flask,Static,Sock host
    class Nginx edge
    class Vol1,Vol2,Vol3,Vol4 vol
```

---

## 12. Cross-Cutting Concerns Summary

| Concern | Mechanism | Location |
|---|---|---|
| **AuthN** | JWT (HS256), `Authorization: Bearer` | `app/services/auth_service.py`, `app/utils/decorators.py` |
| **AuthZ** | Role decorators + resource-owner check | `@token_required`, `@role_required`, `@resource_owner_or_admin` |
| **Token revocation** | In-memory `_TokenBlacklist` until `exp` | `auth_service` |
| **Rate limiting** | Per-endpoint counters (memory or Redis) | `app/middleware/rate_limiting.py` |
| **Realtime** | Flask-Sock `/ws` + room registry | `app/realtime/__init__.py` |
| **Offline mutations** | IndexedDB queue + replay | `frontend/core/offline/offline-queue.js`, `sw-offline-sync.js` |
| **Spatial data** | Normalized (0..1) `x/y` coords on floors | `WorkLog`, `CriticalSector`, `CableRoute` |
| **Image pipeline** | PDF → PIL → DZI tiles (WebP) | `backend/utils/tile_generator_safe.py` |
| **Data safety** | ZIP backup before project delete | `project_backup_service.py` |
| **Migrations** | Idempotent schema creation on startup | `app/database/migrations.py` |
| **Service result** | `ServiceResult` dataclass for uniform API responses | `app/utils/result.py` |

---

## Reading Order Recommendation

For the architecture review, walk the diagrams in this order:

1. **§1 System Context** → who uses it, what's external.
2. **§2 Containers** → how the SPA, API, WS hub, and storage compose.
3. **§5 Domain Model** → the data shape that everything else operates on.
4. **§3 + §4 Module Maps** → backend and frontend internal structure.
5. **§6 Auth** → cross-cutting concern that gates everything.
6. **§7 Realtime** + **§8 Offline** → the two distinguishing capabilities.
7. **§9 Tile Pipeline** → the heaviest single subsystem.
8. **§10 End-to-End** → see all of the above cooperating in one flow.
9. **§11 Deployment** → ops view.

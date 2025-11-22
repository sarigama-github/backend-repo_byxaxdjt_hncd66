import os
from typing import Dict, List, Tuple, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import math

app = FastAPI(title="CDMX Metro A* API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Domain model (static graph)
# ---------------------------

class Station(BaseModel):
    id: str
    name: str
    line: str
    color: str
    x: float
    y: float
    accessible: bool = True  # simplified assumption

# Subset of CDMX lines and stations with approximate coordinates in a normalized plane (0..100)
# Coordinates are rough, only to support a plausible spatial heuristic.
STATIONS: List[Station] = [
    # Line 1 (granate) Observatorio → Balderas
    Station(id="observatorio", name="Observatorio", line="1", color="#8E2046", x=5, y=40),
    Station(id="tacubaya_l1", name="Tacubaya", line="1", color="#8E2046", x=15, y=40),
    Station(id="juanacatlan", name="Juanacatlán", line="1", color="#8E2046", x=25, y=40),
    Station(id="chapultepec", name="Chapultepec", line="1", color="#8E2046", x=35, y=40),
    Station(id="sevilla", name="Sevilla", line="1", color="#8E2046", x=45, y=40),
    Station(id="insurgentes_l1", name="Insurgentes", line="1", color="#8E2046", x=55, y=40),
    Station(id="cuauhtemoc", name="Cuauhtémoc", line="1", color="#8E2046", x=65, y=40),
    Station(id="balderas_l1", name="Balderas", line="1", color="#8E2046", x=70, y=40),

    # Line 3 (verde claro) Universidad → Juárez
    Station(id="universidad", name="Universidad", line="3", color="#6ECF68", x=35, y=95),
    Station(id="copilco", name="Copilco", line="3", color="#6ECF68", x=35, y=90),
    Station(id="ma_quevedo", name="Miguel Ángel de Quevedo", line="3", color="#6ECF68", x=35, y=85),
    Station(id="viveros", name="Viveros/Derechos", line="3", color="#6ECF68", x=35, y=80),
    Station(id="coyoacan", name="Coyoacán", line="3", color="#6ECF68", x=35, y=75),
    Station(id="division", name="División del Norte", line="3", color="#6ECF68", x=45, y=70),
    Station(id="zapata_l3", name="Zapata", line="3", color="#6ECF68", x=55, y=70),
    Station(id="eugenia", name="Eugenia", line="3", color="#6ECF68", x=60, y=65),
    Station(id="etiopia", name="Etiopía/Plaza de la Transparencia", line="3", color="#6ECF68", x=65, y=60),
    Station(id="centro_medico_l3", name="Centro Médico", line="3", color="#6ECF68", x=65, y=55),
    Station(id="hospital_general", name="Hospital General", line="3", color="#6ECF68", x=67, y=50),
    Station(id="ninos_heroes", name="Niños Héroes", line="3", color="#6ECF68", x=69, y=45),
    Station(id="balderas_l3", name="Balderas", line="3", color="#6ECF68", x=70, y=40),
    Station(id="juarez", name="Juárez", line="3", color="#6ECF68", x=72, y=35),

    # Line 7 (naranja) Barranca del Muerto → Polanco
    Station(id="barranca", name="Barranca del Muerto", line="7", color="#F59E0B", x=10, y=85),
    Station(id="mixcoac_l7", name="Mixcoac", line="7", color="#F59E0B", x=20, y=80),
    Station(id="san_antonio", name="San Antonio", line="7", color="#F59E0B", x=25, y=70),
    Station(id="san_pedro", name="San Pedro de los Pinos", line="7", color="#F59E0B", x=25, y=60),
    Station(id="tacubaya_l7", name="Tacubaya", line="7", color="#F59E0B", x=15, y=40),
    Station(id="constituyentes", name="Constituyentes", line="7", color="#F59E0B", x=25, y=35),
    Station(id="auditorio", name="Auditorio", line="7", color="#F59E0B", x=35, y=30),
    Station(id="polanco", name="Polanco", line="7", color="#F59E0B", x=45, y=30),

    # Line 9 (marrón) Tacubaya → Lázaro Cárdenas
    Station(id="tacubaya_l9", name="Tacubaya", line="9", color="#8B5E3C", x=15, y=40),
    Station(id="patriotismo", name="Patriotismo", line="9", color="#8B5E3C", x=35, y=50),
    Station(id="chilpancingo", name="Chilpancingo", line="9", color="#8B5E3C", x=55, y=55),
    Station(id="centro_medico_l9", name="Centro Médico", line="9", color="#8B5E3C", x=65, y=55),
    Station(id="lazaro", name="Lázaro Cárdenas", line="9", color="#8B5E3C", x=75, y=55),

    # Line 12 (verde oscuro) Mixcoac → Eje Central
    Station(id="mixcoac_l12", name="Mixcoac", line="12", color="#065F46", x=20, y=80),
    Station(id="insurgentes_sur", name="Insurgentes Sur", line="12", color="#065F46", x=30, y=75),
    Station(id="h20nov", name="Hospital 20 de Noviembre", line="12", color="#065F46", x=40, y=72),
    Station(id="zapata_l12", name="Zapata", line="12", color="#065F46", x=55, y=70),
    Station(id="parque_venados", name="Parque de los Venados", line="12", color="#065F46", x=60, y=68),
    Station(id="eje_central", name="Eje Central", line="12", color="#065F46", x=70, y=65),
]

# Build lookup maps
STATION_BY_ID: Dict[str, Station] = {s.id: s for s in STATIONS}

# Edges: (u, v, type) where type is 'line' or 'transfer'
EDGES: List[Tuple[str, str, str]] = []

# Helper to connect consecutive on same line

def connect_sequence(ids: List[str]):
    for i in range(len(ids) - 1):
        EDGES.append((ids[i], ids[i+1], 'line'))
        EDGES.append((ids[i+1], ids[i], 'line'))

# Line sequences
connect_sequence(["observatorio","tacubaya_l1","juanacatlan","chapultepec","sevilla","insurgentes_l1","cuauhtemoc","balderas_l1"])
connect_sequence(["universidad","copilco","ma_quevedo","viveros","coyoacan","division","zapata_l3","eugenia","etiopia","centro_medico_l3","hospital_general","ninos_heroes","balderas_l3","juarez"])
connect_sequence(["barranca","mixcoac_l7","san_antonio","san_pedro","tacubaya_l7","constituyentes","auditorio","polanco"])
connect_sequence(["tacubaya_l9","patriotismo","chilpancingo","centro_medico_l9","lazaro"])
connect_sequence(["mixcoac_l12","insurgentes_sur","h20nov","zapata_l12","parque_venados","eje_central"])

# Transfers (bidirectional)
TRANSFERS = [
    ("mixcoac_l7", "mixcoac_l12"),
    ("zapata_l3", "zapata_l12"),
    ("tacubaya_l1", "tacubaya_l7"),
    ("tacubaya_l1", "tacubaya_l9"),
    ("tacubaya_l7", "tacubaya_l9"),
    ("centro_medico_l3", "centro_medico_l9"),
    ("balderas_l1", "balderas_l3"),
]
for a, b in TRANSFERS:
    EDGES.append((a, b, 'transfer'))
    EDGES.append((b, a, 'transfer'))

# -------------
# A* algorithm
# -------------

def dist(a: Station, b: Station) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)

class RouteOptions(BaseModel):
    transfer_penalty: float = Field(5.0, description="Additional cost per transfer")
    mobility: str = Field("normal", description="normal | reduced")
    time_of_day: str = Field("offpeak", description="offpeak | peak")
    prefer_fewer_transfers: bool = False

class RouteRequest(BaseModel):
    origin_id: str
    destination_id: str
    options: RouteOptions = RouteOptions()

class RouteSegment(BaseModel):
    from_id: str
    to_id: str
    type: str  # line | transfer
    line: Optional[str] = None
    distance: float
    cost: float

class RouteResult(BaseModel):
    path: List[str]
    segments: List[RouteSegment]
    total_distance: float
    total_cost: float
    transfers: int
    lines_used: List[str]


def a_star(origin_id: str, destination_id: str, options: RouteOptions) -> RouteResult:
    if origin_id not in STATION_BY_ID or destination_id not in STATION_BY_ID:
        raise HTTPException(status_code=404, detail="Station not found")

    start = STATION_BY_ID[origin_id]
    goal = STATION_BY_ID[destination_id]

    # Build neighbors map with dynamic costs
    neighbors: Dict[str, List[Tuple[str, float, str, Optional[str]]]] = {}
    for u, v, etype in EDGES:
        su, sv = STATION_BY_ID[u], STATION_BY_ID[v]
        base = dist(su, sv)
        cost = base
        line: Optional[str] = None
        if etype == 'transfer':
            # transfer cost includes base distance (walking) + penalty
            cost += options.transfer_penalty
        else:
            line = su.line

        # Mobility adjustment: transfers considered harder for reduced mobility
        if options.mobility == 'reduced' and etype == 'transfer':
            cost *= 1.5

        # Peak time adjustment: penalize some crowded segments (e.g., L3 and L9)
        if options.time_of_day == 'peak' and etype == 'line' and (su.line in {"3", "9"}):
            cost *= 1.15

        neighbors.setdefault(u, []).append((v, cost, etype, line))

    # A*
    open_set = {origin_id}
    came_from: Dict[str, str] = {}
    g_score: Dict[str, float] = {sid: math.inf for sid in STATION_BY_ID}
    g_score[origin_id] = 0.0
    f_score: Dict[str, float] = {sid: math.inf for sid in STATION_BY_ID}
    f_score[origin_id] = dist(start, goal)

    # To also account for transfer count in tie-breaker
    transfers_count: Dict[str, int] = {sid: 0 for sid in STATION_BY_ID}

    while open_set:
        current = min(open_set, key=lambda n: (f_score[n], transfers_count[n]))
        if current == destination_id:
            break
        open_set.remove(current)

        for v, step_cost, etype, line in neighbors.get(current, []):
            tentative = g_score[current] + step_cost
            # Encourage fewer transfers if requested by adding small penalty to g
            if options.prefer_fewer_transfers and etype == 'transfer':
                tentative += 0.5

            if tentative < g_score[v]:
                came_from[v] = current
                g_score[v] = tentative
                f_score[v] = tentative + dist(STATION_BY_ID[v], goal)
                transfers_count[v] = transfers_count[current] + (1 if etype == 'transfer' else 0)
                open_set.add(v)

    if destination_id not in came_from and destination_id != origin_id:
        raise HTTPException(status_code=400, detail="No route found")

    # Reconstruct path
    path_ids = [destination_id]
    while path_ids[-1] != origin_id:
        prev = came_from.get(path_ids[-1])
        if prev is None:
            break
        path_ids.append(prev)
    path_ids.reverse()

    # Build segments and metrics
    segments: List[RouteSegment] = []
    total_distance = 0.0
    total_cost = 0.0
    transfers = 0
    lines_used: List[str] = []

    for a, b in zip(path_ids[:-1], path_ids[1:]):
        # find edge type
        etype = 'line'
        line = STATION_BY_ID[a].line
        if (a, b, 'transfer') in EDGES:
            etype = 'transfer'
            line = None
        d = dist(STATION_BY_ID[a], STATION_BY_ID[b])
        # recompute cost using same rules
        cost = d
        if etype == 'transfer':
            cost += options.transfer_penalty
            if options.mobility == 'reduced':
                cost *= 1.5
            transfers += 1
        else:
            if options.time_of_day == 'peak' and STATION_BY_ID[a].line in {"3", "9"}:
                cost *= 1.15
            if line not in lines_used:
                lines_used.append(line)

        segments.append(RouteSegment(from_id=a, to_id=b, type=etype, line=line, distance=d, cost=cost))
        total_distance += d
        total_cost += cost

    return RouteResult(
        path=path_ids,
        segments=segments,
        total_distance=round(total_distance, 3),
        total_cost=round(total_cost, 3),
        transfers=transfers,
        lines_used=lines_used,
    )


@app.get("/")
def read_root():
    return {"message": "CDMX Metro A* Backend running"}


@app.get("/api/stations", response_model=List[Station])
def get_stations():
    return STATIONS


@app.post("/api/route", response_model=RouteResult)
def compute_route(req: RouteRequest):
    if req.origin_id == req.destination_id:
        s = STATION_BY_ID.get(req.origin_id)
        if not s:
            raise HTTPException(status_code=404, detail="Station not found")
        return RouteResult(
            path=[s.id], segments=[], total_distance=0.0, total_cost=0.0, transfers=0, lines_used=[s.line]
        )
    return a_star(req.origin_id, req.destination_id, req.options)


@app.get("/test")
def test_database():
    """Connectivity + env check (DB is optional for this app)."""
    response = {
        "backend": "✅ Running",
        "database": "ℹ️ Not required for this app",
        "database_url": "Optional",
        "database_name": "Optional",
        "connection_status": "Not Used",
        "collections": []
    }
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

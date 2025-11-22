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
    line: str  # '1'..'12', 'A', 'B'
    color: str
    x: float  # 0..100 schematic coordinates (west->east)
    y: float  # 0..100 schematic coordinates (south->north)
    order: int  # sequential order along line to draw polylines
    accessible: bool = True

# Official-ish colors (approx hex)
LINE_COLORS: Dict[str, str] = {
    "1": "#E03C8A",  # Rosa mexicano
    "2": "#003CA6",  # Azul marino
    "3": "#6EBD45",  # Verde olivo/bandera medio
    "4": "#A7D5EB",  # Cian
    "5": "#FFCE00",  # Amarillo
    "6": "#D52B1E",  # Rojo oscuro
    "7": "#F5A300",  # Naranja
    "8": "#00A94F",  # Verde bandera
    "9": "#A05D2D",  # Café claro
    "10": "#9D9D9D",  # no usada
    "11": "#9D9D9D",  # no usada
    "12": "#C6B200",  # Dorado
    "A": "#9F69B5",  # Morado claro
    "B": "#7B7D7D",  # Gris
}

STATIONS: List[Station] = []
EDGES: List[Tuple[str, str, str]] = []  # (u, v, 'line'|'transfer')


def add_line(line: str, names: List[Tuple[str, str, float, float]]):
    color = LINE_COLORS[line]
    start_idx = len([s for s in STATIONS if s.line == line])
    ids: List[str] = []
    for i, (sid, name, x, y) in enumerate(names, start=1):
        STATIONS.append(Station(id=sid, name=name, line=line, color=color, x=x, y=y, order=i))
        ids.append(sid)
    # connect sequence bidirectionally
    for i in range(len(ids) - 1):
        EDGES.append((ids[i], ids[i+1], 'line'))
        EDGES.append((ids[i+1], ids[i], 'line'))


# ---------------------------
# Lines (schematic coordinates)
# ---------------------------
# Coordinates are approximate to achieve a clean schematic with N up, E right.

# Line 1: Observatorio → Pantitlán
add_line("1", [
    ("l1_observatorio", "Observatorio", 4, 44),
    ("l1_tacubaya", "Tacubaya", 12, 44),
    ("l1_juanacatlan", "Juanacatlán", 20, 44),
    ("l1_chapultepec", "Chapultepec", 28, 44),
    ("l1_sevilla", "Sevilla", 36, 44),
    ("l1_insurgentes", "Insurgentes", 44, 44),
    ("l1_cuauhtemoc", "Cuauhtémoc", 52, 44),
    ("l1_balderas", "Balderas", 58, 44),
    ("l1_salto_del_agua", "Salto del Agua", 62, 44),
    ("l1_isabel_la_catolica", "Isabel la Católica", 66, 44),
    ("l1_pino_suarez", "Pino Suárez", 70, 44),
    ("l1_merced", "Merced", 74, 44),
    ("l1_candelaria", "Candelaria", 78, 44),
    ("l1_san_lazaro", "San Lázaro", 82, 44),
    ("l1_moctezuma", "Moctezuma", 86, 44),
    ("l1_balbuena", "Balbuena", 90, 44),
    ("l1_boulevard_pz", "Boulevard Pto. Aéreo", 94, 44),
    ("l1_puebla", "Puebla", 96, 44),
    ("l1_pantitlan", "Pantitlán", 98, 44),
])

# Line 2: Cuatro Caminos → Tasqueña
add_line("2", [
    ("l2_cuatro_caminos", "Cuatro Caminos", 2, 72),
    ("l2_panteones", "Panteones", 8, 68),
    ("l2_tacuba", "Tacuba", 12, 64),
    ("l2_cuitlahuac", "Cuitláhuac", 18, 60),
    ("l2_popotla", "Popotla", 22, 58),
    ("l2_colegio_militar", "Colegio Militar", 26, 56),
    ("l2_normal", "Normal", 30, 54),
    ("l2_san_cosme", "San Cosme", 38, 52),
    ("l2_revolucion", "Revolución", 46, 50),
    ("l2_hidalgo", "Hidalgo", 54, 48),
    ("l2_bellas_artes", "Bellas Artes", 60, 46),
    ("l2_allende", "Allende", 66, 46),
    ("l2_zocalo", "Zócalo/Tenochtitlan", 70, 48),
    ("l2_san_antonio_abad", "San Antonio Abad", 70, 56),
    ("l2_chabacano", "Chabacano", 70, 62),
    ("l2_ermita", "Ermita", 70, 72),
    ("l2_general_anaya", "General Anaya", 70, 78),
    ("l2_tasquena", "Tasqueña", 70, 84),
])

# Line 3: Indios Verdes → Universidad
add_line("3", [
    ("l3_indios_verdes", "Indios Verdes", 58, 4),
    ("l3_dep_18_marzo", "Deportivo 18 de Marzo", 58, 10),
    ("l3_la_raza", "La Raza", 58, 16),
    ("l3_tlatelolco", "Tlatelolco", 58, 22),
    ("l3_guerrero", "Guerrero", 58, 28),
    ("l3_hidalgo", "Hidalgo", 56, 48),
    ("l3_juarez", "Juárez", 60, 42),
    ("l3_ninos_heroes", "Niños Héroes", 62, 38),
    ("l3_c_medico", "Centro Médico", 66, 34),
    ("l3_etiopia", "Etiopía", 66, 28),
    ("l3_eugenia", "Eugenia", 64, 24),
    ("l3_zapata", "Zapata", 60, 22),
    ("l3_division", "División del Norte", 56, 20),
    ("l3_coyoacan", "Coyoacán", 52, 18),
    ("l3_ma_quevedo", "Miguel Ángel de Quevedo", 48, 16),
    ("l3_copilco", "Copilco", 44, 14),
    ("l3_universidad", "Universidad", 40, 12),
])

# Line 4: Martín Carrera → Santa Anita (diagonal NE→S)
add_line("4", [
    ("l4_martin_carrera", "Martín Carrera", 82, 8),
    ("l4_talisman", "Talismán", 80, 14),
    ("l4_bondojito", "Bondojito", 78, 18),
    ("l4_consulado", "Consulado", 76, 22),
    ("l4_morelos", "Morelos", 72, 32),
    ("l4_candelaria", "Candelaria", 78, 44),
    ("l4_fray_servando", "Fray Servando", 76, 50),
    ("l4_jamaica", "Jamaica", 74, 56),
    ("l4_santa_anita", "Santa Anita", 72, 62),
])

# Line 5: Politécnico → Pantitlán
add_line("5", [
    ("l5_poli", "Politécnico", 46, 6),
    ("l5_inst_petroleo", "Instituto del Petróleo", 52, 10),
    ("l5_la_raza", "La Raza", 58, 16),
    ("l5_misterios", "Misterios", 66, 18),
    ("l5_consulado", "Consulado", 76, 22),
    ("l5_aragon", "Aragón", 84, 24),
    ("l5_oceania", "Oceanía", 90, 28),
    ("l5_terminal_aerea", "Terminal Aérea", 92, 34),
    ("l5_hangares", "Hangares", 94, 38),
    ("l5_pantitlan", "Pantitlán", 98, 44),
])

# Line 6: El Rosario → Martín Carrera
add_line("6", [
    ("l6_el_rosario", "El Rosario", 8, 8),
    ("l6_tezozomoc", "Tezozómoc", 14, 10),
    ("l6_azcapotzalco", "Azcapotzalco", 20, 12),
    ("l6_ferreria", "Ferrería/Arena CDMX", 28, 14),
    ("l6_vallejo", "Vallejo", 36, 16),
    ("l6_inst_petroleo", "Instituto del Petróleo", 52, 10),
    ("l6_lindavista", "Lindavista", 62, 12),
    ("l6_dep_18_marzo", "Deportivo 18 de Marzo", 58, 10),
    ("l6_la_villa", "La Villa–Basílica", 70, 10),
    ("l6_martin_carrera", "Martín Carrera", 82, 8),
])

# Line 7: El Rosario → Barranca del Muerto
add_line("7", [
    ("l7_el_rosario", "El Rosario", 8, 8),
    ("l7_aquiles_serdan", "Aquiles Serdán", 10, 20),
    ("l7_tacuba", "Tacuba", 12, 64),
    ("l7_san_joaquin", "San Joaquín", 18, 58),
    ("l7_polanco", "Polanco", 24, 52),
    ("l7_auditorio", "Auditorio", 28, 48),
    ("l7_constituyentes", "Constituyentes", 20, 44),
    ("l7_tacubaya", "Tacubaya", 12, 44),
    ("l7_san_pedro_pinos", "San Pedro de los Pinos", 12, 52),
    ("l7_san_antonio", "San Antonio", 12, 60),
    ("l7_mixcoac", "Mixcoac", 12, 68),
    ("l7_barranca", "Barranca del Muerto", 12, 78),
])

# Line 8: Garibaldi → Constitución de 1917
add_line("8", [
    ("l8_garibaldi", "Garibaldi", 62, 36),
    ("l8_bellas_artes", "Bellas Artes", 60, 46),
    ("l8_san_juan_letran", "San Juan de Letrán", 62, 48),
    ("l8_salto_del_agua", "Salto del Agua", 62, 44),
    ("l8_doctores", "Doctores", 64, 54),
    ("l8_obrera", "Obrera", 66, 58),
    ("l8_chabacano", "Chabacano", 70, 62),
    ("l8_la_viga", "La Viga", 72, 66),
    ("l8_santa_anita", "Santa Anita", 72, 62),
    ("l8_coyuya", "Coyuya", 76, 66),
    ("l8_iztacalco", "Iztacalco", 80, 68),
    ("l8_apatlaco", "Apatlaco", 84, 70),
    ("l8_aculco", "Aculco", 86, 72),
    ("l8_escuadron201", "Escuadrón 201", 88, 74),
    ("l8_atlalilco", "Atlalilco", 90, 76),
    ("l8_iztapalapa", "Iztapalapa", 92, 78),
    ("l8_cerro_estrella", "Cerro de la Estrella", 94, 80),
    ("l8_uam_i", "UAM I", 96, 82),
    ("l8_const_1917", "Constitución de 1917", 98, 84),
])

# Line 9: Tacubaya → Pantitlán
add_line("9", [
    ("l9_tacubaya", "Tacubaya", 12, 44),
    ("l9_patriotismo", "Patriotismo", 24, 46),
    ("l9_chilpancingo", "Chilpancingo", 36, 48),
    ("l9_c_medico", "Centro Médico", 66, 34),
    ("l9_lazaro_cardenas", "Lázaro Cárdenas", 72, 40),
    ("l9_chabacano", "Chabacano", 70, 62),
    ("l9_jamaica", "Jamaica", 74, 56),
    ("l9_mixiuhca", "Mixiuhca", 86, 48),
    ("l9_velodromo", "Velódromo", 90, 46),
    ("l9_ciudad_deportiva", "Ciudad Deportiva", 94, 46),
    ("l9_puebla", "Puebla", 96, 44),
    ("l9_pantitlan", "Pantitlán", 98, 44),
])

# Line 12: Mixcoac → Tláhuac (partial important nodes)
add_line("12", [
    ("l12_mixcoac", "Mixcoac", 12, 68),
    ("l12_insurgentes_sur", "Insurgentes Sur", 20, 66),
    ("l12_h20nov", "Hospital 20 de Noviembre", 28, 64),
    ("l12_zapata", "Zapata", 60, 22),
    ("l12_parque_venados", "Parque de los Venados", 64, 20),
    ("l12_eje_central", "Eje Central", 68, 18),
    ("l12_ermita", "Ermita", 70, 72),
    ("l12_mexicaltzingo", "Mexicaltzingo", 78, 74),
    ("l12_atlalilco", "Atlalilco", 90, 76),
    ("l12_culhuacan", "Culhuacán", 88, 72),
    ("l12_san_andres", "San Andrés Tomatlán", 86, 70),
    ("l12_lomas_estrella", "Lomas Estrella", 84, 68),
    ("l12_calle_11", "Calle 11", 82, 66),
    ("l12_periferico", "Periférico Oriente", 80, 64),
    ("l12_tezonco", "Tezonco", 78, 62),
    ("l12_olivos", "Olivos", 76, 60),
    ("l12_nopalera", "Nopalera", 74, 58),
    ("l12_zapotitlan", "Zapotitlán", 72, 56),
    ("l12_tlaltenco", "Tlaltenco", 70, 54),
    ("l12_tlahuac", "Tláhuac", 68, 52),
])

# Line A: Pantitlán → La Paz
add_line("A", [
    ("la_pantitlan", "Pantitlán", 98, 44),
    ("la_agricola", "Agrícola Oriental", 96, 48),
    ("la_canal_san_juan", "Canal de San Juan", 94, 52),
    ("la_tepaclates", "Tepalcates", 92, 56),
    ("la_guelatao", "Guelatao", 90, 60),
    ("la_penon_viejo", "Peñón Viejo", 88, 64),
    ("la_acatitla", "Acatitla", 86, 68),
    ("la_santa_marta", "Santa Marta", 84, 72),
    ("la_la_paz", "La Paz", 82, 78),
])

# Line B: Buenavista → Ciudad Azteca
add_line("B", [
    ("lb_buenavista", "Buenavista", 52, 34),
    ("lb_guerrero", "Guerrero", 58, 28),
    ("lb_garibaldi", "Garibaldi", 62, 36),
    ("lb_lagunilla", "Lagunilla", 66, 34),
    ("lb_tepito", "Tepito", 68, 32),
    ("lb_morelos", "Morelos", 72, 32),
    ("lb_san_lazaro", "San Lázaro", 82, 44),
    ("lb_r_flores_magon", "R. Flores Magón", 86, 38),
    ("lb_romero_rubio", "Romero Rubio", 88, 34),
    ("lb_oceania", "Oceanía", 90, 28),
    ("lb_dep_oceania", "Deportivo Oceanía", 92, 22),
    ("lb_bosque_aragon", "Bosque de Aragón", 94, 18),
    ("lb_villa_aragon", "Villa de Aragón", 96, 16),
    ("lb_nego", "Nezahualcóyotl", 98, 14),
    ("lb_impulsora", "Impulsora", 98, 12),
    ("lb_rio_remedios", "Río de los Remedios", 98, 10),
    ("lb_muzquiz", "Múzquiz", 98, 8),
    ("lb_ciudad_azteca", "Ciudad Azteca", 98, 6),
])

# Lookup map
STATION_BY_ID: Dict[str, Station] = {s.id: s for s in STATIONS}

# Transfers (bidirectional) based on user's schematic
TRANSFERS: List[Tuple[str, str]] = [
    # Tacubaya (1-7-9)
    ("l1_tacubaya", "l7_tacubaya"),
    ("l1_tacubaya", "l9_tacubaya"),
    ("l7_tacubaya", "l9_tacubaya"),

    # Pantitlán (1-5-9-A)
    ("l1_pantitlan", "l5_pantitlan"),
    ("l1_pantitlan", "l9_pantitlan"),
    ("l1_pantitlan", "la_pantitlan"),
    ("l5_pantitlan", "l9_pantitlan"),
    ("l5_pantitlan", "la_pantitlan"),
    ("l9_pantitlan", "la_pantitlan"),

    # Hidalgo (2-3)
    ("l2_hidalgo", "l3_hidalgo"),

    # Bellas Artes (2-8)
    ("l2_bellas_artes", "l8_bellas_artes"),

    # Pino Suárez (1-2)
    ("l1_pino_suarez", "l2_san_antonio_abad"),  # close in schematic, primary transfer is at Pino Suárez; approximate

    # Chabacano (2-8-9)
    ("l2_chabacano", "l8_chabacano"),
    ("l2_chabacano", "l9_chabacano"),
    ("l8_chabacano", "l9_chabacano"),

    # Candelaria (1-4)
    ("l1_candelaria", "l4_candelaria"),

    # Jamaica (4-9)
    ("l4_jamaica", "l9_jamaica"),

    # Santa Anita (4-8)
    ("l4_santa_anita", "l8_santa_anita"),

    # Consulado (4-5)
    ("l4_consulado", "l5_consulado"),

    # Oceanía (5-B)
    ("l5_oceania", "lb_oceania"),

    # San Lázaro (1-B)
    ("l1_san_lazaro", "lb_san_lazaro"),

    # Morelos (4-B)
    ("l4_morelos", "lb_morelos"),

    # Guerrero (3-B)
    ("l3_guerrero", "lb_guerrero"),

    # Garibaldi (8-B)
    ("l8_garibaldi", "lb_garibaldi"),

    # Zapata (3-12)
    ("l3_zapata", "l12_zapata"),

    # Mixcoac (7-12)
    ("l7_mixcoac", "l12_mixcoac"),

    # Centro Médico (3-9)
    ("l3_c_medico", "l9_c_medico"),

    # Balderas (1-3)
    ("l1_balderas", "l3_juarez"),  # schematic closeness; Balderas-Juárez area
]

for a, b in TRANSFERS:
    if a in STATION_BY_ID and b in STATION_BY_ID:
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
            cost += options.transfer_penalty
        else:
            line = su.line

        if options.mobility == 'reduced' and etype == 'transfer':
            cost *= 1.5

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

    transfers_count: Dict[str, int] = {sid: 0 for sid in STATION_BY_ID}

    while open_set:
        current = min(open_set, key=lambda n: (f_score[n], transfers_count[n]))
        if current == destination_id:
            break
        open_set.remove(current)

        for v, step_cost, etype, line in neighbors.get(current, []):
            tentative = g_score[current] + step_cost
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
        etype = 'line'
        line = STATION_BY_ID[a].line
        if (a, b, 'transfer') in EDGES:
            etype = 'transfer'
            line = None
        d = dist(STATION_BY_ID[a], STATION_BY_ID[b])
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
    return {
        "backend": "✅ Running",
        "database": "ℹ️ Not required for this app",
        "database_url": "Optional",
        "database_name": "Optional",
        "connection_status": "Not Used",
        "collections": []
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

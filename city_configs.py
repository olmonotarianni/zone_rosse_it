from dataclasses import dataclass

@dataclass
class CityConfig:
    city_name: str
    city_pattern: str  # For API searches
    default_bbox: tuple[float, float, float, float]  # south, west, north, east
    zone_bboxes: dict[str, tuple[float, float, float, float]]
    zone_mappings: dict[str, str]
    special_cases: dict[str, list[str]]


def create_rome_config() -> CityConfig:
    return CityConfig(
        city_name="Roma",
        city_pattern="Roma",
        default_bbox=(41.8, 12.4, 42.0, 12.6),
        zone_bboxes={
            'esquilino': (41.888, 12.495, 41.905, 12.52),
            'tuscolano': (41.85, 12.512, 41.883, 12.56),
            'valle_aurelia': (41.889, 12.41, 41.925, 12.46)
        },
        zone_mappings={
            'zona_esquilino': 'esquilino',
            'zona_stazione_termini_esquilino': 'esquilino',
            'zona_tuscolano': 'tuscolano',
            'zona_valle_aurelia': 'valle_aurelia',
            'assi_viari_inclusi_nel_perimetro_zona_valle_aurelia': 'valle_aurelia'
        },
        special_cases={
            "la marmora": ["La Marmora", "Lamarmora"],
            "sottopasso": ["Sottopasso", "Sottopassaggio"],
            "pettinelli": ["Turbigo"],
            # Common abbreviations and variants
            "turati": ["Filippo Turati", "F. Turati"],
            "giolitti": ["Giovanni Giolitti", "G. Giolitti"],
            "amendola": ["Giovanni Amendola", "G. Amendola"],
            "giacinto de vecchi pieralice": ["Pieralice"],

        }
    )

def create_milan_config() -> CityConfig:
    return CityConfig(
        city_name="Milano", 
        city_pattern="Milano",
        default_bbox=(45.352097,8.980637,45.590120,9.385071),
        zone_bboxes={
            'zona_duomo': (45.460, 9.175, 45.470, 9.205),
            'navigli_darsena_colonne': (45.440, 9.160, 45.465, 9.195),
            'stazione_centrale': (45.468, 9.192, 45.494, 9.215),
            'stazione_porta_garibaldi': (45.475, 9.178, 45.495, 9.198),
            'stazione_rogoredo': (45.418, 9.210, 45.445, 9.250),
            'rozzano': (45.360970, 9.120197, 45.408020, 9.201908),
            'via_padova': (45.481992, 9.211702, 45.511592, 9.253951),
        },
        zone_mappings={
            'zona_navigli': 'navigli_darsena_colonne',
            'darsena_e_navigli': 'navigli_darsena_colonne',
            'zona_darsena_e_navigli': 'navigli_darsena_colonne',
            'colonne_di_san_lorenzo': 'navigli_darsena_colonne',
            'duomo': 'zona_duomo',
            'zona_stazione_centrale': 'stazione_centrale',
            'zona_porta_garibaldi': 'stazione_porta_garibaldi',
            'zona_rogoredo': 'stazione_rogoredo',
            'stazione_ffss_centrale': 'stazione_centrale',
            'stazione_ffss_porta_garibaldi': 'stazione_porta_garibaldi',
            'stazione_ffss_rogoredo': 'stazione_rogoredo',
            'rozzano_quartiere_dei_fiori': 'rozzano',
            'via_padova': 'via_padova',
        },
        special_cases={
            "duomo": ["Duomo", "Piazza del Duomo", "Piazza Duomo"],
            "scala": ["La Scala", "Teatro alla Scala", "Piazza della Scala"],
            "castello": ["Castello Sforzesco", "Castello"],
            "bocconi": ["Università Bocconi", "Via Bocconi"],
            "centrale": ["Stazione Centrale", "Milano Centrale"],
            "garibaldi": ["Porta Garibaldi", "Stazione Garibaldi"],
            "rogoredo": ["Stazione Rogoredo"],
            "cadorna": ["Cadorna", "Stazione Cadorna"],
            "loreto": ["Piazzale Loreto"],
            "corvetto": ["Corvetto", "Piazzale Luigi Emanuele Corvetto", "Piazzale Corvetto"],
            "gabrio rosa": ["Gabriele Rosa", "Piazzale Gabriele Rosa"],
            "meda": ["Filippo Meda"],
            "diaz": ["Armando Diaz", "Generale Armando Diaz"],
            "porta genova": ["Pta Genova", "P.ta Genova"],
            "xxiv maggio (lato mercato comunale/darsena)": ["Mercato Comunale Ticinese", "Darsena"],
            "corso di porta ticinese (lato numero pari)": ["Corso di Porta Ticinese", "Corso di P.ta Ticinese"],
            " (lato numeri pari)": "",
            "colonne di san lorenzo": ["San Lorenzo"],
            "baden powell": ["B.-Powell", "Baden-Powell", "B. Powell"],
            "padova": ["Viale Padova"],
            "cordusio": ["Piazzale Cordusio"],
            "dei gerani": ["delle mimose"]
        }
    )

def create_bologna_config() -> CityConfig:
    return CityConfig(
        city_name="Bologna",
        city_pattern="Bologna",
        default_bbox=(44.45, 11.25, 44.55, 11.40),
        
        zone_bboxes={
            'centro_storico': (44.490, 11.335, 44.505, 11.355),   
            'bolognina': (44.500325, 11.330073, 44.524318, 11.365108)
            },
        
        zone_mappings={
            'centro_storico': 'centro_storico',
            'zona_bolognina': 'bolognina'
        },
        
        special_cases={
        }
    )

def create_padova_config() -> CityConfig:
    return CityConfig(
        city_name="Padova",
        city_pattern="Padova",
        default_bbox= (45.364979, 11.825855, 45.445488, 11.925435),
        
        zone_bboxes={
            'stazione_ferroviaria': (45.411442, 11.870238, 45.424275, 11.889816),   
            'arcella': (45.416841, 11.868553, 45.430094, 11.900153)
            },
        
        zone_mappings={
            'centro_storico': 'centro_storico',
            'quartiere_arcella': 'arcella'
        },
        
        special_cases={
            ' (confine nord)': [""],
            ' (confine sud)': [""],
            ' (confine est)': [""],
            ' (confine ovest)': [""],
            'Card. Callegari': ["Cardinale Callegari", "Callegari"],
            "Area antistante all'autostazione": ["autostazione"],
            "antistante all'autostazione": ["autostazione"],
            "antistante": ["autostazione"],
        }
    )

CITIES = {
    'RM': create_rome_config(),
    'MI': create_milan_config(),
    'PD': create_padova_config(),
    'BO': create_bologna_config()
}

CITY_PREFIXES = {
    'Roma': 'RM',
    'Milano': 'MI',
    'Padova': 'PD',
    'Bologna': 'BO'
}

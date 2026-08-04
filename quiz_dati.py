"""
Banca dati delle domande per i quiz spaziali.

Ogni domanda e' una tupla: (testo della domanda, lista di 4 opzioni,
indice della risposta corretta nella lista). Argomenti disponibili:
Apollo, NASA, ESA, Esplorazione spaziale.
"""

DOMANDE = {
    "Apollo": [
        ("In che anno l'Apollo 11 sbarco sulla Luna?",
         ["1965", "1969", "1972", "1961"], 1),
        ("Chi fu il primo essere umano a camminare sulla Luna?",
         ["Buzz Aldrin", "Michael Collins", "Neil Armstrong", "John Glenn"], 2),
        ("Quale missione Apollo ebbe un'esplosione a bordo ma rientro sana e salva?",
         ["Apollo 8", "Apollo 13", "Apollo 1", "Apollo 10"], 1),
        ("Quale astronauta rimase in orbita lunare durante lo sbarco dell'Apollo 11?",
         ["Michael Collins", "Buzz Aldrin", "Jim Lovell", "David Scott"], 0),
        ("Qual e' stata l'ultima missione Apollo con sbarco sulla Luna?",
         ["Apollo 15", "Apollo 16", "Apollo 17", "Apollo 14"], 2),
    ],
    "NASA": [
        ("In che anno fu fondata la NASA?",
         ["1958", "1961", "1969", "1972"], 0),
        ("Come si chiama il programma NASA per il ritorno sulla Luna?",
         ["Apollo", "Artemis", "Orion", "Constellation"], 1),
        ("Qual e' il principale centro di lancio della NASA in Florida?",
         ["Johnson Space Center", "Kennedy Space Center", "Ames Research Center", "Goddard"], 1),
        ("Quale rover NASA e' attualmente attivo su Marte dal 2021?",
         ["Curiosity", "Opportunity", "Perseverance", "Spirit"], 2),
        ("Quale veicolo commerciale ha riportato gli USA a lanciare equipaggi dal suolo americano nel 2020?",
         ["Starliner", "Crew Dragon", "Orion", "Dream Chaser"], 1),
    ],
    "ESA": [
        ("In che anno fu fondata l'ESA (Agenzia Spaziale Europea)?",
         ["1975", "1980", "1969", "1990"], 0),
        ("Da quale base equatoriale lancia solitamente i suoi razzi l'ESA?",
         ["Baikonur", "Kourou", "Cape Canaveral", "Vandenberg"], 1),
        ("Chi fu la prima astronauta italiana nello spazio?",
         ["Samantha Cristoforetti", "Paolo Nespoli", "Luca Parmitano", "Umberto Guidoni"], 0),
        ("Come si chiama il razzo europeo di nuova generazione?",
         ["Ariane 6", "Vega C", "Falcon 9", "Sojuz"], 0),
        ("A quale missione ESA e' associata la sonda Rosetta, famosa per l'atterraggio su una cometa?",
         ["Missione su Marte", "Missione sulla cometa 67P", "Missione sulla Luna", "Missione su Venere"], 1),
    ],
    "Esplorazione spaziale": [
        ("Qual e' stato il primo satellite artificiale della storia?",
         ["Explorer 1", "Sputnik 1", "Vanguard 1", "Telstar 1"], 1),
        ("Chi fu il primo essere umano nello spazio?",
         ["Alan Shepard", "John Glenn", "Yuri Gagarin", "Neil Armstrong"], 2),
        ("Quale stazione spaziale ha preceduto la ISS, lanciata dagli Stati Uniti negli anni '70?",
         ["Mir", "Skylab", "Salyut", "Tiangong"], 1),
        ("Quale azienda privata ha sviluppato il primo razzo riutilizzabile su larga scala?",
         ["Blue Origin", "SpaceX", "Rocket Lab", "Virgin Galactic"], 1),
        ("Qual e' il pianeta piu vicino al Sole?",
         ["Venere", "Terra", "Mercurio", "Marte"], 2),
    ],
}

# Soglie di punti totali (somma dei punteggi di tutti i quiz svolti) per
# sbloccare ogni badge, dal piu semplice al piu prestigioso.
SOGLIE_BADGE = [
    (5, "🥉 Appassionato"),
    (15, "🥈 Esperto"),
    (30, "🥇 Storico Spaziale"),
    (50, "🚀 Comandante"),
]

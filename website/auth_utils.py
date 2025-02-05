from flask import session
from .utils import hashPassword

# funktio joka palauttaa kilpailut sekä vuosiluvut
def get_competitions_with_year(cur):
    cur.execute("SELECT kisaid, nimi, alkuaika FROM kilpailut")
    kilpailut = cur.fetchall()
    kilpailutjaVuosi = []
    
    for kilpailu in kilpailut:
        alkuaika = kilpailu["alkuaika"]
        if alkuaika:
            vuosi = alkuaika.year
        else:
            vuosi = None

        kilpailutjaVuosi.append({
            'kisaid': kilpailu['kisaid'],
            'nimi': kilpailu['nimi'],
            'vuosi': vuosi
        })

    return sorted(kilpailutjaVuosi, key=lambda k: k['nimi'])

# Onko joukkue olemassa ja salasana oikein
def authenticate_team(cur, tunnus, salasana, valittuKilpailuId):
    # haetaan tiimin id ja salasana
    cur.execute("""SELECT nimi, joukkueid, salasana FROM joukkueet WHERE nimi = %s""", (tunnus,))
    joukkueidJaSalasana = cur.fetchone()

    if not joukkueidJaSalasana:
        return False, "Kirjautuminen epäonnistui"
    
    joukkueid = joukkueidJaSalasana['joukkueid']
    storedHashedPassword = joukkueidJaSalasana['salasana']
    hashedInputPassword = hashPassword(joukkueid, salasana)

    # Haetaan kilpailun sarjat
    cur.execute("""SELECT sarjaid FROM sarjat WHERE kilpailu = %s""", (valittuKilpailuId,))
    sarjat = cur.fetchall()

    # Onko tiimi olemassa valitussa kilpailussa
    for sarja in sarjat:
        sarja_id = sarja["sarjaid"]
        cur.execute("""SELECT nimi FROM joukkueet WHERE sarja = %s AND nimi = %s""", (sarja_id, tunnus))
        joukkue = cur.fetchone()

        if joukkue and hashedInputPassword == storedHashedPassword:
            return True, joukkueid 
    
    return False, "Kirjautuminen epäonnistui: virheellinen salasana"

# Jos kirjautuminen onnistuu, asetetaan tarvittavat sessiot
def set_session_variables(cur, session, joukkueid, valittuKilpailuId, tunnus):
    cur.execute("""SELECT joukkueid, nimi FROM joukkueet WHERE joukkueid = %s""", (joukkueid,))
    joukkue = cur.fetchone()
    
    if joukkue:
        session['joukkueid'] = joukkue['joukkueid']
        session['käyttäjä'] = joukkue['nimi']
        session['kirjautunut'] = "ok"
    
    # haetaan kilpailun tiedot
    cur.execute("SELECT nimi, alkuaika, kisaid FROM kilpailut WHERE kisaid = %s", (valittuKilpailuId,))
    kilpailu = cur.fetchone()
    
    if kilpailu:
        session['valittuKilpailuId'] = valittuKilpailuId
        session['kilpailu_nimi'] = kilpailu['nimi']
        session['kilpailu_pvm'] = kilpailu['alkuaika']

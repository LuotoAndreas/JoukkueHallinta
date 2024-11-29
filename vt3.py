from datetime import datetime
import os
import sqlite3
from flask import Flask, flash, request, Response, render_template, session, redirect, url_for
from jinja2 import Template, Environment, FileSystemLoader
from functools import wraps
import json
import urllib
import hashlib

app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config.update(
    SESSION_COOKIE_SAMESITE='Lax'
)
app.secret_key = b'U\xfc\x92"DGw\xff\xcfG\x06\x90\xe7\x9d\x9d\xc7~\xee\xe3\xf1\xc2\xb8\xcb\xa5'

def admin_auth(f):
    ''' TÃ¤mÃ¤ decorator hoitaa kirjautumisen tarkistamisen ja ohjaa tarvittaessa kirjautumissivulle
    '''
    @wraps(f)
    def decorated(*args, **kwargs):
        # tÃ¤ssÃ¤ voisi olla monimutkaisempiakin tarkistuksia mutta yleensÃ¤ tÃ¤mÃ¤ riittÃ¤Ã¤        
        if not 'adminKirjautunut' in session:
            return redirect(url_for('admin'))
        return f(*args, **kwargs)
    return decorated

def auth(f):
    ''' TÃ¤mÃ¤ decorator hoitaa kirjautumisen tarkistamisen ja ohjaa tarvittaessa kirjautumissivulle
    '''
    @wraps(f)
    def decorated(*args, **kwargs):
        # tÃ¤ssÃ¤ voisi olla monimutkaisempiakin tarkistuksia mutta yleensÃ¤ tÃ¤mÃ¤ riittÃ¤Ã¤        
        if not 'kirjautunut' in session:
            return redirect(url_for('kirjaudu'))
        return f(*args, **kwargs)
    return decorated

@app.route("/", methods=["GET", "POST"])
@auth
def home():            
    return redirect(url_for('kirjaudu'))

@app.route('/admin',methods=['GET', 'POST'])
def admin(): 
    
    if request.method == "POST":
        tunnus = request.form.get("tunnus")
        salasana = request.form.get("salasana")   
        error_message = ""                 
            
        if not tunnus or not salasana:
            error_message = "Syötä tunnus ja salasana"
            return render_template("kirjauduAdmin.html", error_message=error_message)

        # salasanan hashaus
        avain = u"jokujokuavain"
        salasana = hashPassword(avain, salasana)    
        
        if tunnus == "admin" and salasana == '96d3cf4d4fe8e5ea39207038ce45a89a37b985c5f85dd4af9d68629c2895caaa947cab7bf9ba570883b14684476ed7d0208f6eaec079d34d1a486b672e472cc9':
            session['adminKirjautunut'] = "ok"
            return redirect(url_for('adminPaasivu'))
        else:
            error_message = "väärä tunnus tai salasana"
            return render_template("kirjauduAdmin.html", error_message=error_message)
            
    return render_template("kirjauduAdmin.html")

@app.route('/adminPaasivu',methods=['GET', 'POST'])
@admin_auth
def adminPaasivu(): 
    try:
    # yhdistetään tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")

        cur = con.cursor()

        # haetaan kilpailut ja vuosiluvut
        cur. execute("SELECT kisaid, nimi, DATE(alkuaika) AS alkuaika FROM kilpailut ORDER BY alkuaika ASC")
        kilpailut = cur.fetchall()

        
        return render_template("adminKilpailut.html", kilpailut=kilpailut, sarjaid=session.get('sarjaid'), joukkueid=session.get('joukkueid'), kisaid=session.get('kisaid'))
    
    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        con.close()


@app.route('/kilpailu/<int:kisaid>', methods=['GET', 'POST'])
@admin_auth
def kilpailu(kisaid):
    session['kisaid'] = kisaid
    try:
        # yhdistetään tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")

        cur = con.cursor()

        # haetaan sarjat jotka kuuluvat kilpailuun
        cur.execute("""SELECT sarjaid, nimi FROM sarjat WHERE kilpailu = ?""", (kisaid,))
        sarjat = cur.fetchall()

        return render_template("adminSarjat.html", sarjat=sarjat, sarjaid=session.get('sarjaid'), joukkueid=session.get('joukkueid'), kisaid=kisaid)
        
    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        con.close()


@app.route('/sarja/<int:sarjaid>',  methods=['GET', 'POST'])
@admin_auth
def sarja(sarjaid):
    session['sarjaid'] = sarjaid
    try:
        # yhdistetään tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")

        cur = con.cursor()

        # haetaan joukkueet jotka kuuluvat sarjaan
        cur.execute("""SELECT joukkueid, nimi FROM joukkueet WHERE sarja = ?""", (sarjaid,))
        joukkueet = cur.fetchall()

        if request.method == "POST":
            handleJoukkueLisaaminen()

            # haetaan päivitetyt joukkueet, että nähdään uusi joukkue heti sivulla
            cur.execute("""SELECT joukkueid, nimi FROM joukkueet WHERE sarja = ?""", (sarjaid,))
            joukkueet = cur.fetchall()   
  
        return render_template("adminSarjanJoukkueet.html", joukkueet=joukkueet, sarjaid=sarjaid, joukkueid=session.get('joukkueid'), kisaid=session.get('kisaid'))
    
    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        con.close()


@app.route('/joukkue/<int:joukkueid>', methods=['GET', 'POST'])
@admin_auth
def joukkue(joukkueid):
    session['joukkueid'] = joukkueid
    try: 
        kisaid = session.get('kisaid')

        # yhdistetään tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")

        cur = con.cursor()       

        # haetaan joukkueet jotka kuuluvat sarjaan
        cur.execute("""SELECT * FROM joukkueet WHERE joukkueid = ?""", (joukkueid,))
        joukkue = cur.fetchone()

        if joukkue:
            jasenet = json.loads(joukkue['jasenet'])
        else:
            jasenet = []

        # Haetaan sarja johon tämä joukkue kuuluu
        sarja_id = joukkue['sarja']

        # Haetaan kilpailu johon tämä sarja kuuluu
        cur.execute("""SELECT kilpailu FROM sarjat WHERE sarjaid = ?""", (sarja_id,))
        kilpailu_id = cur.fetchone()['kilpailu']

        # Haetaan kaikki sarjat jotka kuuluvat tähän kilpailuun
        cur.execute("""SELECT * FROM sarjat WHERE kilpailu = ?""", (kilpailu_id,))
        sarjat = cur.fetchall()                   

        # POST pyyntö
        if request.method == "POST":
            if 'delete_joukkue' in request.form:
                result = handleJoukkueenPoistaminen()

                # jos tulee errorviesti, palautetaan sama sivu viestin kanssa
                if result and result.get("error_message"):
                        return render_template(
                            "adminJoukkueTiedot.html", 
                            joukkue=joukkue,
                            sarjat=sarjat,
                            jasenet=jasenet,
                            kisaid=kisaid,
                            sarjaid=session.get('sarjaid'),
                            joukkueid=joukkueid,
                            error_message=result["error_message"])

                # palataan sarjan joukkueet -sivulle jos ei erroreita
                return redirect(url_for('sarja', sarjaid=session.get('sarjaid')))
            else:
                # Päivitetään joukkueen tiedot käyttämällä handleJoukkueUpdate funktiota
                result = handleJoukkueUpdate(request, con, cur, joukkueid, joukkue, sarjat, jasenet)

                # Tarkistetaan, onko virheilmoitus
                if result["error_message"]:
                    return render_template(
                        "adminJoukkueTiedot.html",
                        joukkue=joukkue,
                        sarjat=sarjat,
                        jasenet=jasenet,
                        kisaid=kisaid,
                        sarjaid=session.get('sarjaid'),
                        joukkueid=joukkueid,
                        error_message=result["error_message"]
                    )

                # haetaan päivitetyt tiedot tallennuksen jälkeen
                cur.execute("""SELECT * FROM joukkueet WHERE joukkueid = ?""", (joukkueid,))
                joukkue = cur.fetchone()
                jasenet = json.loads(joukkue['jasenet']) if joukkue['jasenet'] else []

                # Päivitetty onnistuneesti, palataan takaisin joukkueen tietoihin
                return render_template(
                    "adminJoukkueTiedot.html",
                    joukkue=joukkue,
                    sarjat=sarjat,
                    jasenet=jasenet,
                    kisaid=kisaid,
                    sarjaid=session.get('sarjaid'),
                    joukkueid=joukkueid
                )       
        
        # renderöidään näkymä GET pyynnölle
        return render_template(
            "adminJoukkueTiedot.html",
            joukkue=joukkue,
            sarjat=sarjat,
            jasenet=jasenet,
            kisaid=kisaid,
            sarjaid=session.get('sarjaid'),
            joukkueid=joukkueid
        )

    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        con.close()



@app.route('/tiedot', methods=['GET', 'POST'])
@auth
def tiedot():
    try:
        # Haetaan kilpailun tiedot sessiosta
        joukkueid = session.get('joukkueid')
        kilpailu_nimi = session.get('kilpailu_nimi')
        kilpailu_pvm = session.get('kilpailu_pvm')
        kilpailuid = session.get('valittuKilpailuId')

        # Yhdistä tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row  # Mahdollistaa sanakirjatulokset
        con.execute("PRAGMA foreign_keys = ON")

        cur = con.cursor()

        # Haetaan joukkueen tiedot
        joukkue = cur.execute("""
            SELECT nimi, salasana, sarja, jasenet
            FROM joukkueet
            WHERE joukkueid = ?
        """, (joukkueid,)).fetchone()

        # Muunnetaan jäsenet listaksi
        jasenet_list = json.loads(joukkue['jasenet']) if joukkue['jasenet'] else []

        # Haetaan sarjat kilpailusta
        cur.execute('SELECT * FROM sarjat WHERE kilpailu = ?', (kilpailuid,))
        sarjat = cur.fetchall()

        # Handle POST requests
        if request.method == "POST":
            result = handleJoukkueUpdate(request, con, cur, joukkueid, joukkue, sarjat, jasenet_list)
            # jos tulee errorviesti, palautetaan sama sivu viestin kanssa
            if result["error_message"]:
                return render_template(
                    "joukkuetiedot.html",
                    kilpailu_nimi=kilpailu_nimi,
                    joukkue=joukkue,
                    sarjat=sarjat,
                    jasenet=jasenet_list,
                    kilpailu_pvm=kilpailu_pvm,
                    error_message=result["error_message"],
                )

            # jos päivitys on onnistunut niin ohjataan joukkueet sivulle
            return redirect(url_for("joukkueet"))

        # renderöidään joukkuetiedot sivu
        return render_template(
            "joukkuetiedot.html",
            kilpailu_nimi=kilpailu_nimi,
            kilpailu_pvm=kilpailu_pvm,
            joukkue=joukkue,
            sarjat=sarjat,
            jasenet=jasenet_list,
        )

    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        con.close()

# apufunktio salasanan suojaamiseen
def hashPassword(joukkueid, salasana):
    m = hashlib.sha512()
    m.update(str(joukkueid).encode("UTF-8"))
    m.update(salasana.encode("UTF-8"))
    return m.hexdigest()


# joukkueen tietojen muokkaus ja tallennus 
def handleJoukkueUpdate(request, con, cur, joukkueid, joukkue, sarjat, jasenet_list):
   
    joukkueenNimi = request.form.get("nimi", "").strip()
    salasana = request.form.get("salasana", "").strip()
    sarja = request.form.get("sarja")
    jasenet = [jasen.strip() for jasen in request.form.getlist('jasenet[]') if jasen.strip()]

    # jos uusi salasana on syötetty lomakkeeseen niin se hashataan     
    if salasana:       
        salasana = hashPassword(joukkueid, salasana)

    # varmistetaan että joukkueen nimi on syötetty
    if not joukkueenNimi:
        return {"error_message": "Joukkueen nimi ei saa olla tyhjä!"}
    
    # jäseniä tulee olla vähintään kaksi
    if len(jasenet) < 2:
        return {"error_message": "Joukkueessa tulee olla vähintään 2 jäsentä"}

    # jäsenillä on ainutlaatuiset nimet
    if len(jasenet) != len(set(map(str.lower, jasenet))):
        return {"error_message": "Jäsenet eivät saa olla saman nimisiä!"}

    # joukkueen nimi on ainutlaatuinen
    cur.execute("""
        SELECT COUNT(*) 
        FROM joukkueet 
        WHERE LOWER(nimi) = LOWER(?) AND sarja = ? AND joukkueid != ?
    """, (joukkueenNimi, sarja, joukkueid))

    if cur.fetchone()[0] > 0:
        return {"error_message": "Joukkueen nimi on jo käytössä samassa kilpailussa ja sarjassa!"}

    # serialisoidaan jäsenet
    jasenet_json = json.dumps(jasenet)

    try:
        cur.execute(
            """
            UPDATE joukkueet
            SET nimi = ?, salasana = ?, sarja = ?, jasenet = ?
            WHERE joukkueid = ?
            """,
            (joukkueenNimi, salasana, sarja, jasenet_json, joukkueid),
        )
        con.commit()
        return {"error_message": None}  # No errors
    except sqlite3.IntegrityError:
        return {"error_message": "Joukkueen nimi on jo käytössä."}

# joukkueen lisääminen
def handleJoukkueLisaaminen():
    nimi = request.form.get("nimi")
    salasana = request.form.get("salasana")
    sarja = session.get('sarjaid')
    jasenet = [jasen.strip() for jasen in request.form.getlist('jasenet[]') if jasen.strip()]
    joukkueid = session.get('joukkueid')

    # muutetaan jäsenet jsoniin
    jasenet_json = json.dumps(jasenet)

    # hashataan salasana
    salasana = hashPassword(joukkueid, salasana)
    try:

    # yhdistetään tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")

        cur = con.cursor()       

        # alustetaan joukkueen lisääminen halutuilla tiedoilla
        cur.execute("""INSERT INTO joukkueet (nimi, salasana, jasenet, sarja) 
                    VALUES (?, ?, ?, ?)""", (nimi, salasana, jasenet_json, sarja))
        
        con.commit()   

    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        con.close()

# joukkueen poistava funktio
def handleJoukkueenPoistaminen():    
    joukkueid = session.get('joukkueid')
    sarjaid = session.get('sarjaid')

    try:        
    # yhdistetään tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")

        cur = con.cursor() 

        # haetaan ne rastit, jotka kuuluvat tupaan jotka kuuluvat joukkueeseen
        cur.execute("""SELECT rastit.* FROM rastit JOIN tupa ON tupa.rasti = rastit.id WHERE tupa.joukkue = ?""", (joukkueid,))
        rasti = cur.fetchone()

        # jos joukkueella on rasteja, palautetaan vain error viesti eikä suoriteta joukkueen poistoa loppuun
        if rasti:
            return {"error_message": "Ei voi poistaa, joukkueella on rastileimauksia"}
        
        # alustetaan joukkueen poisto
        cur.execute("""DELETE FROM joukkueet WHERE joukkueid = ?""", (joukkueid,))
        con.commit()      

        # poistetaan poistetun joukkuen id sessiosta
        session['joukkueid'] = None  

        con.commit()        
    
    except sqlite3.Error as e:
        return {"error_message": f"Tietokanta ei aukene: {str(e)}"}
    except Exception as e:
        return {"error_message": f"Tapahtui virhehöhö: {str(e)}"}

    finally:
        con.close()
            


@app.route('/kirjaudu',methods=['GET', 'POST'])
def kirjaudu():    

    try:
        
        # yhdistetään tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")

        cur = con.cursor()

        # haetaan kilpailut ja vuosiluvut
        cur.execute("SELECT kisaid, nimi, alkuaika FROM kilpailut")
        kilpailut = cur.fetchall()
        kilpailutjaVuosi = []

        # haetaan vuosiluku
        for kilpailu in kilpailut:
            alkuaika = kilpailu["alkuaika"]
            if alkuaika:
                # muunnetaan alkuaika datetime-objektiksi
                vuosi = datetime.strptime(alkuaika, '%Y-%m-%d %H:%M:%S').year
            else:
                vuosi = None 

            # Lisätään uusi kilpailu, joka sisältää myös vuosiluvun
            kilpailutjaVuosi.append({
                'kisaid': kilpailu['kisaid'],
                'nimi': kilpailu['nimi'],
                'vuosi': vuosi
            })
        
        # kilpailut aakkosjärjestykseen
        kilpailutjaVuosi = sorted(kilpailutjaVuosi, key=lambda k: k['nimi'])
    
        if request.method == "POST":            

            # haetaan lomakkeesta syötetyt tiedot
            tunnus = request.form.get("tunnus")
            salasana = request.form.get("salasana")            
            valittuKilpailuId = request.form.get("kilpailu") 

            if not tunnus or not salasana or not valittuKilpailuId:
                error_message = "valitse kilpailu ja syötä tunnus sekä salasana"
                return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi, error_message=error_message)
            
            # haetaan joukkueenId ja salattu salasana tunnuksen mukaan
            cur. execute("""SELECT joukkueid, salasana FROM joukkueet WHERE nimi = ?""", (tunnus,))
            joukkueidJaSalasana = cur.fetchone()

            # jos käyttäjätunnus on väärin
            if not joukkueidJaSalasana:
                error_message = "Kirjautuminen epäonnistui"
                return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi, error_message=error_message)

            joukkueid = joukkueidJaSalasana['joukkueid']
            hashedSalasana = joukkueidJaSalasana['salasana']

            # hashataan salasana ja vertaillaan joukkueid:n mukaan
            salasana = hashPassword(joukkueid, salasana)

            # haetaan sarjat
            sarjat = cur.execute("""
                SELECT sarjaid FROM sarjat WHERE kilpailu = ?
            """, (valittuKilpailuId,)).fetchall()

            # tarkistetaan onko joukkuenimi olemassa sarjassa joka on valitussa kilpailussa
            team_exists = False
            for sarja in sarjat:
                sarja_id = sarja["sarjaid"]

                # haetaan joukkue 
                joukkue = cur.execute("""
                    SELECT nimi FROM joukkueet
                    WHERE sarja = ? AND nimi = ?
                """, (sarja_id, tunnus)).fetchone()

                if joukkue:
                    team_exists = True
                    break
        
            if team_exists and salasana == hashedSalasana:
                # jos kaikki ok niin asetetaan sessioon tieto kirjautumisesta ja ohjataan laskurisivulle
                session['kirjautunut'] = "ok"
                session['valittuKilpailuId'] = valittuKilpailuId

                joukkue = cur.execute("""
                    SELECT joukkueid, nimi FROM joukkueet
                    WHERE sarja = ? AND nimi = ?
                    """, (sarja_id, tunnus)).fetchone()
                
                if joukkue:
                    session['joukkueid'] = joukkue['joukkueid']  # Tallennetaan joukkueen ID
                    session['käyttäjä'] = joukkue['nimi'] 

                # haetaan kilpailun nimi ja päivämäärä tietokannasta
                kilpailu = cur.execute("SELECT nimi, alkuaika, kisaid FROM kilpailut WHERE kisaid = ?", (valittuKilpailuId,)).fetchone()
                if kilpailu:
                    session['kilpailu_nimi'] = kilpailu['nimi']
                    session['kilpailu_pvm'] = kilpailu['alkuaika']

                # salasanan ja tunnuksen ollessa oikein ohjataan pääsivulle
                return redirect(url_for('joukkueet'))
            
            else:
                error_message = "Kirjautuminen epäonnistui: virheellinen salasana"
                return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi, error_message=error_message)

        # GET pyynnössä renderöidään kirjaudu sivu
        return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi)
    
    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except UnicodeDecodeError as e:
        return Response(f"Merkkikoodauksen virhe: {str(e)}", status=500)
    finally:
        con.close()


@app.route('/logout', methods=['POST'])
def logout():    
    isAdmin = session.get('adminKirjautunut')
    session.clear()
    #session.pop('kirjautunut', None)
    #session.pop('valittuKilpailuId', None)
    #session.pop('kilpailu_nimi', None)
    #session.pop('kilpailu_pvm', None)
    #session.pop('käyttäjä', None)
    #session.pop('jasenet', None)
    #session.pop('joukkueid', None)
    #session.pop('pvmIlmanAikaa', None)
    #session.pop('adminKirjautunut', None)
    
    if isAdmin == "ok":
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('kirjaudu'))


@app.route('/joukkueet')
@auth
def joukkueet():
    try:
        kisaId = session.get('valittuKilpailuId')  
        käyttäjä = session.get('käyttäjä')      

        # Yhdistä tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row  # Mahdollistaa tulosten käsittelyn dict-tyyppisinä
        con.execute("PRAGMA foreign_keys = ON")  # Ota foreign keys käyttöön

        cur = con.cursor()

        # haetaan kilpailuun liittyvät sarjat aakkosjärjestyksessä
        cur.execute('SELECT * FROM sarjat WHERE kilpailu = ? ORDER BY LOWER(nimi)', (kisaId,))
        sarjat = cur.fetchall()  # Haetaan sarjat kilpailusta       

        # haetaan kaikki joukkueet aakkosjärjestyksessä 
        cur.execute('SELECT * FROM joukkueet ORDER BY LOWER(nimi)')        
        joukkueet = cur.fetchall()
        
        joukkueetSarjassa = []
        for sarja in sarjat:
            for joukkue in joukkueet:
                if joukkue['sarja'] == sarja['sarjaid']:
                    joukkueetSarjassa.append(joukkue)

        jasenet = {}
        for joukkue in joukkueet:
            cur.execute('SELECT jasenet FROM joukkueet WHERE joukkueid = ?', (joukkue['joukkueid'],))
            jasenetData = cur.fetchone()
            if jasenetData:
                jasenet[joukkue['joukkueid']] = json.loads(jasenetData['jasenet'])        

        # päivämäärä ilman kellonakaa ylävalikkoa varten
        pvmIlmanAikaa = session.get('kilpailu_pvm').split(' ')[0]

        kilpailu = {
            'nimi': session.get('kilpailu_nimi'),
            'pvm': pvmIlmanAikaa
        }          
        
        return render_template('joukkueet.html', sarjat=sarjat, joukkueet=joukkueet, jasenet=jasenet, kilpailu=kilpailu, käyttäjä=käyttäjä)

    except sqlite3.Error as e:
        # Virhe tietokannan kanssa
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except UnicodeDecodeError as e:
        # Virhe merkkikoodauksessa
        return Response(f"Merkkikoodauksen virhe: {str(e)}", status=500)
    finally:
        # Varmista, että yhteys suljetaan aina
        con.close()
   
if __name__ == '__main__':
    app.run(debug=True)



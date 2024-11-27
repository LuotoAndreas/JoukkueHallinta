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

        # tunnuksen hashaus (en ole varma tarviiko tätä tehdä)
        u = hashlib.sha512()
        avain2 = u"jokujokuavain"
        u.update(avain2.encode("UTF-8"))   
        u.update(tunnus.encode("UTF-8"))  

        # salasanan hashaus
        m = hashlib.sha512()
        avain = u"jokujokuavain"
        m.update(avain.encode("UTF-8"))
        m.update(salasana.encode("UTF-8"))      
        
        if u.hexdigest() == '96d3cf4d4fe8e5ea39207038ce45a89a37b985c5f85dd4af9d68629c2895caaa947cab7bf9ba570883b14684476ed7d0208f6eaec079d34d1a486b672e472cc9' and m.hexdigest() == '96d3cf4d4fe8e5ea39207038ce45a89a37b985c5f85dd4af9d68629c2895caaa947cab7bf9ba570883b14684476ed7d0208f6eaec079d34d1a486b672e472cc9':
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

        
        return render_template("adminKilpailut.html", kilpailut=kilpailut)
    
    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        con.close()


@app.route('/kilpailu/<int:kisaid>')
def kilpailu(kisaid):

    try:
        # yhdistetään tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")

        cur = con.cursor()

        # haetaan sarjat jotka kuuluvat kilpailuun
        cur.execute("""SELECT sarjaid, nimi FROM sarjat WHERE kilpailu = ?""", (kisaid,))
        sarjat = cur.fetchall()

        return render_template("adminSarjat.html", sarjat=sarjat)
        
    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        con.close()


@app.route('/sarja/<int:sarjaid>')
def sarja(sarjaid):
    try:
        # yhdistetään tietokantaan
        con = sqlite3.connect(os.path.abspath('tietokanta.db'))
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")

        cur = con.cursor()

        # haetaan joukkueet jotka kuuluvat sarjaan
        cur.execute("""SELECT joukkueid, nimi FROM joukkueet WHERE sarja = ?""", (sarjaid,))
        joukkueet = cur.fetchall()

        return render_template("adminSarjanJoukkueet.html", joukkueet=joukkueet)
    
    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        con.close()


@app.route('/joukkue/<int:joukkueid>')
def joukkue(joukkueid):
    try: 
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


        return render_template("adminJoukkueTiedot.html", joukkue=joukkue, sarjat=sarjat, jasenet=jasenet)

    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

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
        cur. execute("SELECT kisaid, nimi, alkuaika FROM kilpailut")
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

            tunnus = request.form.get("tunnus")
            salasana = request.form.get("salasana")            
            valittuKilpailuId = request.form.get("kilpailu")

            print(f'valittu kilpialu id: {valittuKilpailuId}')

            if not tunnus or not salasana:
                error_message = "Syötä Joukkue ja salasana"
                return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi, error_message=error_message)

            if not valittuKilpailuId:
                error_message = "valitse kilpailu"
                return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi, error_message=error_message)

            m = hashlib.sha512()
            avain = u"jokujokuavain"
            m.update(avain.encode("UTF-8"))
            m.update(salasana.encode("UTF-8"))


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
        
            if team_exists and m.hexdigest() == '0dc39cbd493c6990b28fd313b35cabf352f6af50db32b222f053815d57d8bd2ff783bf8e134807946d9f587dd084e66185ff4f3370154615e08c745c1b6fcb58':
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

                return redirect(url_for('joukkueet'))
        
        # jos ei ollut oikea salasana niin pysytÃ¤Ã¤n kirjautumissivulla.         
        return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi)
    
    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except UnicodeDecodeError as e:
        return Response(f"Merkkikoodauksen virhe: {str(e)}", status=500)
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

        if request.method == "POST":
            joukkueenNimi = request.form.get("nimi").strip()
            salasana = request.form.get("salasana").strip()  
            sarja = request.form.get("sarja")
            jasenet = [jasen.strip() for jasen in request.form.getlist('jasenet') if jasen.strip()]
            error_message = ""
            
            # Tarkistetaan, että joukkueen nimi ei ole tyhjä
            if not joukkueenNimi:
                error_message = "Joukkueen nimi ei saa olla tyhjä!"
                # Jos virheilmoitus on, palauta lomake takaisin
                return render_template("joukkuetiedot.html", 
                                       kilpailu_nimi=kilpailu_nimi, 
                                       kilpailu_pvm=kilpailu_pvm, 
                                       joukkue=joukkue,  # Lähetetään nykyiset joukkueen tiedot
                                       sarjat=sarjat,     # Lähetetään kaikki sarjat
                                       jasenet=jasenet_list,  # Lähetetään jäsenet
                                       error_message=error_message)  # Virheilmoitus palautetaan
            
            # Tarkistetaan, että joukkueen nimi ei ole jo käytössä samassa kilpailussa ja sarjassa
            cur.execute("""
                SELECT COUNT(*) 
                FROM joukkueet 
                WHERE LOWER(nimi) = LOWER(?) AND sarja = ? AND joukkueid != ?
            """, (joukkueenNimi, sarja, joukkueid))

            if cur.fetchone()[0] > 0:
                error_message = "Joukkueen nimi on jo käytössä samassa kilpailussa ja sarjassa!"
                return render_template("joukkuetiedot.html", 
                                       kilpailu_nimi=kilpailu_nimi, 
                                       kilpailu_pvm=kilpailu_pvm, 
                                       joukkue=joukkue,  
                                       sarjat=sarjat,     
                                       jasenet=jasenet_list,  
                                       error_message=error_message)
            
            if len(jasenet) < 2:
                error_message = "Joukkueessa tulee olla vähintään 2 jäsentä"
                return render_template("joukkuetiedot.html", 
                                       kilpailu_nimi=kilpailu_nimi, 
                                       kilpailu_pvm=kilpailu_pvm, 
                                       joukkue=joukkue,  # Lähetetään nykyiset joukkueen tiedot
                                       sarjat=sarjat,     # Lähetetään kaikki sarjat
                                       jasenet=jasenet_list,  # Lähetetään jäsenet
                                       error_message=error_message)  # Virheilmoitus palautetaan
            
            # Tarkistetaan, että kaikki jäsenten nimet ovat uniikkeja (case insensitive)
            if len(jasenet) != len(set(map(lambda x: x.lower(), jasenet))):
                error_message = "Jäsenet eivät saa olla saman nimisiä!"
                return render_template("joukkuetiedot.html", 
                                       kilpailu_nimi=kilpailu_nimi, 
                                       kilpailu_pvm=kilpailu_pvm, 
                                       jasenet=jasenet, 
                                       error_message=error_message, 
                                       joukkue=joukkue, 
                                       sarjat=sarjat)
            
            jasenet_json = json.dumps(jasenet)

            try:
                cur.execute("""
                    UPDATE joukkueet
                    SET nimi = ?, salasana = ?, sarja = ?, jasenet = ?
                    WHERE joukkueid = ?
                """, (joukkueenNimi, salasana, sarja, jasenet_json, joukkueid))
                con.commit()

                return redirect(url_for('joukkueet'))
            except sqlite3.IntegrityError:
                flash('Joukkueen nimi on jo käytössä.')
            finally:
                con.close()

        # Palautetaan tiedot mallipohjaan ilman virheilmoitusta
        return render_template(
            "joukkuetiedot.html",
            kilpailu_nimi=kilpailu_nimi,
            kilpailu_pvm=kilpailu_pvm,
            joukkue=joukkue,
            sarjat=sarjat,
            jasenet=jasenet_list
        )

    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

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

        # haetaan kilpailuun liittyvät sarjat
        cur.execute('SELECT * FROM sarjat WHERE kilpailu = ?', (kisaId,))
        sarjat = cur.fetchall()  # Haetaan sarjat kilpailusta       

        # Lajitellaan sarjat aakkosjärjestykseen
        sarjat = sorted(sarjat, key=lambda sarja: sarja['nimi'].lower()) 
        
        # haetaan kaikki joukkueet 
        cur.execute('SELECT * FROM joukkueet')        
        joukkueet = cur.fetchall()

        
        joukkueetSarjassa = []
        for sarja in sarjat:
            for joukkue in joukkueet:
                if joukkue['sarja'] == sarja['sarjaid']:
                    joukkueetSarjassa.append(joukkue)
        
        joukkueet = sorted(joukkueetSarjassa, key=lambda k: k['nimi'])  # Joukkueet aakkosjärjestykseen
        
        joukkueDict = [dict(joukkue) for joukkue in joukkueet]
        session['joukkueet'] = joukkueDict


        jasenet = {}
        for joukkue in joukkueet:
            cur.execute('SELECT jasenet FROM joukkueet WHERE joukkueid = ?', (joukkue['joukkueid'],))
            jasenetData = cur.fetchone()
            if jasenetData:
                jasenet[joukkue['joukkueid']] = json.loads(jasenetData['jasenet'])  
        
        
        session['jasenet'] = jasenet

        session['pvmIlmanAikaa'] = session.get('kilpailu_pvm').split(' ')[0]

        kilpailu = {
            'nimi': session.get('kilpailu_nimi'),
            'pvm': session.get('pvmIlmanAikaa')
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



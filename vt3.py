from datetime import datetime
import os
import sqlite3
from flask import Flask, request, Response, render_template, session, redirect, url_for
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

@app.route('/kirjaudu',methods=['GET', 'POST'])
def kirjaudu():    

    message = ""
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

            if not valittuKilpailuId:
                message = "valitse kilpailu"
                return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi, message=message)

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

                # haetaan kilpailun nimi ja päivämäärä tietokannasta
                kilpailu = cur.execute("SELECT nimi, alkuaika FROM kilpailut WHERE kisaid = ?", (valittuKilpailuId,)).fetchone()
                if kilpailu:
                    session['kilpailu_nimi'] = kilpailu['nimi']
                    session['kilpailu_pvm'] = kilpailu['alkuaika']
                session['käyttäjä'] = tunnus  # Tallennetaan käyttäjänimi sessioon

                return redirect(url_for('joukkueet'))
        
        # jos ei ollut oikea salasana niin pysytÃ¤Ã¤n kirjautumissivulla.         
        return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi)
    
    except sqlite3.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except UnicodeDecodeError as e:
        return Response(f"Merkkikoodauksen virhe: {str(e)}", status=500)
    finally:
        con.close()

@app.route('/logout', methods=['POST'])
def logout():

   session.pop('kirjautunut', None)
   session.pop('valittuKilpailuId', None)
   session.pop('kilpailu_nimi', None)
   session.pop('kilpailu_pvm', None)
   session.pop('käyttäjä', None)
   return redirect(url_for('kirjaudu'))


@app.route('/joukkueet')
@auth
def joukkueet():
    try:
        kisaId = session.get('valittuKilpailuId')        

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

        jasenet = {}
        for joukkue in joukkueet:
            cur.execute('SELECT jasenet FROM joukkueet WHERE joukkueid = ?', (joukkue['joukkueid'],))
            jasenetData = cur.fetchone()
            if jasenetData:
                jasenet[joukkue['joukkueid']] = json.loads(jasenetData['jasenet'])  

        kilpailu = {
            'nimi': session.get('kilpailu_nimi'),
            'pvm': session.get('kilpailu_pvm')
        }
        
        käyttäjä = session.get('käyttäjä')

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



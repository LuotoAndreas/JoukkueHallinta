import json
from multiprocessing import pool
from flask import Blueprint, render_template, request, redirect, url_for, session, Response
import mysql
from website import create_app
from .utils import auth


views = Blueprint('views', __name__)

@views.route("/", methods=["GET", "POST"])
@auth  
def home():
    return redirect(url_for('auth.kirjaudu')) 


@views.route('/joukkueet')
@auth
def joukkueet():
    try:
        kisaId = session.get('valittuKilpailuId')  
        käyttäjä = session.get('käyttäjä')      

        # luodaan yhteys tietokantaan
        con = create_app().pool.get_connection()
        cur = con.cursor(dictionary = True)

        # haetaan kilpailuun liittyvät sarjat aakkosjärjestyksessä
        cur.execute('SELECT * FROM sarjat WHERE kilpailu = %s ORDER BY LOWER(nimi)', (kisaId,))
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
            cur.execute('SELECT jasenet FROM joukkueet WHERE joukkueid = %s', (joukkue['joukkueid'],))
            jasenetData = cur.fetchone()
            if jasenetData:
                jasenet[joukkue['joukkueid']] = json.loads(jasenetData['jasenet'])        

        # päivämäärä ilman kellonakaa ylävalikkoa varten
        pvmIlmanAikaa = session.get('kilpailu_pvm').strftime('%Y-%m-%d')

        kilpailu = {
            'nimi': session.get('kilpailu_nimi'),
            'pvm': pvmIlmanAikaa
        }          
        
        return render_template('joukkueet.html', sarjat=sarjat, joukkueet=joukkueet, jasenet=jasenet, kilpailu=kilpailu, käyttäjä=käyttäjä)

    except mysql.connector.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui joukkueet virhe: {str(e)}", status=500)

    finally:
        if con and con.is_connected():
            cur.close()
            con.close()



from .utils import admin_auth
@views.route('/kilpailut', methods=['GET', 'POST'])
@admin_auth  
def kilpailut():
    kisaid = request.args.get('kisaid')
    if kisaid:
        # Jos uusi kilpailu valitaan, resetoidaan sessiot 
        if kisaid != session.get('kisaid'):
            session['sarjaid'] = None
            session['joukkueid'] = None
        session['kisaid'] = kisaid
        session['jasentenLukumaara'] = 5
        return redirect(url_for('views.kilpailu', kisaid=kisaid)) 
    
    try:
        con = create_app().pool.get_connection()
        cur = con.cursor(dictionary=True)

        # haetaan kilpailu ja vuosi
        cur.execute("SELECT kisaid, nimi, DATE(alkuaika) AS alkuaika FROM kilpailut ORDER BY alkuaika ASC")
        kilpailut = cur.fetchall()    
        
        return render_template("adminKilpailut.html", kilpailut=kilpailut, sarjaid=session.get('sarjaid'), joukkueid=session.get('joukkueid'), kisaid=session.get('kisaid'))
    
    except mysql.connector.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        if con and con.is_connected():
            cur.close()
            con.close()

@views.route('/kilpailu/<int:kisaid>', methods=['GET', 'POST'])
@admin_auth 
def kilpailu(kisaid):
    if not session.get('kisaid'):
        return redirect(url_for('views.kilpailut'))

    sarjaid = request.args.get('sarjaid')
    if sarjaid:
        session['sarjaid'] = sarjaid
        session['jasentenLukumaara'] = 5
        return redirect(url_for('views.sarja', sarjaid=sarjaid)) 
    
    try:
        con = create_app().pool.get_connection()
        cur = con.cursor(dictionary=True)

        # Haetaan kilpailun nimi
        cur.execute("SELECT nimi FROM kilpailut WHERE kisaid = %s", (kisaid,))
        kilpailu = cur.fetchone()
        kilpailu_nimi = kilpailu['nimi'] if kilpailu else None
        session['kilpailuNimi'] = kilpailu_nimi

        # Haetaan kilpailun sarja
        cur.execute("SELECT sarjaid, nimi FROM sarjat WHERE kilpailu = %s ORDER BY LOWER(nimi)", (kisaid,))
        sarjat = cur.fetchall()

        return render_template("adminSarjat.html", sarjat=sarjat, sarjaid=session.get('sarjaid'), joukkueid=session.get('joukkueid'), kisaid=kisaid)
    
    except mysql.connector.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        if con.is_connected():
            cur.close()
            con.close()


@views.route('/rastit', methods=['GET', 'POST'])
@admin_auth 
def rastit():
    try:
        con = create_app().pool.get_connection()
        cur = con.cursor(dictionary=True)

        # Haetaan kaikki rastit sekä niiden leimaukset
        cur.execute("""
            SELECT rastit.koodi, rastit.id, rastit.lat, rastit.lon, rastit.kilpailu, COUNT(tupa.rasti) AS leimaukset_count
            FROM rastit
            LEFT OUTER JOIN tupa ON rastit.id = tupa.rasti
            WHERE rastit.kilpailu = %s
            GROUP BY rastit.id
            ORDER BY leimaukset_count DESC
        """, (session.get('kisaid'),))

        rasti_leimaukset = cur.fetchall()

        return render_template('adminRastit.html', rastit=rasti_leimaukset)
    
    except mysql.connector.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        if con.is_connected():
            cur.close()
            con.close()


@views.route('/sarja/<int:sarjaid>', methods=['GET', 'POST'])
@admin_auth   
def sarja(sarjaid):
    from .utils import handleJoukkueLisaaminen
     
    if not session.get('sarjaid'):
        if session.get('kisaid'):
            return redirect(url_for('views.kilpailu', kisaid=session.get('kisaid')))
        else:
            return redirect(url_for('views.kilpailut'))

    joukkueid = request.args.get('joukkueid')
    if joukkueid:
        session['joukkueid'] = joukkueid
        return redirect(url_for('views.joukkue', joukkueid=joukkueid))  # Redirect to team page

    try:
        con = create_app().pool.get_connection()
        cur = con.cursor(dictionary=True)

        # haetaan sarjojen nimet
        cur.execute("SELECT nimi FROM sarjat WHERE sarjaid = %s", (sarjaid,))
        sarja = cur.fetchone()
        sarja_nimi = sarja['nimi'] if sarja else None
        session['sarjaNimi'] = sarja_nimi

        # Haetaan joukkueet, jotka kuuluvat sarjaan
        cur.execute("SELECT joukkueid, nimi FROM joukkueet WHERE sarja = %s", (sarjaid,))
        joukkueet = cur.fetchall()

        jasentenLukumaara = session.get('jasentenLukumaara', 5)
       
        if request.method == "POST":
            # jäsenten lisäys
            if 'add_more' in request.form:
                jasentenLukumaara += 1
                session['jasentenLukumaara'] = jasentenLukumaara
                nimi = request.form.get('nimi', '')
                jasenet = request.form.getlist('jasenet[]')
                salasana = request.form.get('salasana', '')
                return render_template("adminSarjanJoukkueet.html", 
                                       joukkueet=joukkueet, 
                                       sarjaid=sarjaid, 
                                       joukkueid=session.get('joukkueid'), 
                                       kisaid=session.get('kisaid'), 
                                       jasentenLukumaara=jasentenLukumaara,
                                       nimi=nimi,
                                       salasana=salasana,
                                       jasenet=jasenet)
            
            # Joukkueiden päivitys lisäyksen jälkeen
            cur.execute("SELECT joukkueid, nimi FROM joukkueet WHERE sarja = %s", (sarjaid,))
            joukkueet = cur.fetchall()

            result = handleJoukkueLisaaminen(con, cur) 
            
            # Palautetaan sama sivu error viestillä jos epäonnistuu
            if result["error_message"]:
                return render_template("adminSarjanJoukkueet.html", 
                                       joukkueet=joukkueet, 
                                       sarjaid=sarjaid, 
                                       joukkueid=session.get('joukkueid'), 
                                       kisaid=session.get('kisaid'),
                                       error_message=result["error_message"], 
                                       jasentenLukumaara=jasentenLukumaara)
            
             # Haetaan joukkuetiedot uudestaan
            cur.execute("SELECT joukkueid, nimi FROM joukkueet WHERE sarja = %s", (sarjaid,))
            joukkueet = cur.fetchall()
            
        return render_template("adminSarjanJoukkueet.html", 
                               joukkueet=joukkueet, 
                               sarjaid=sarjaid, 
                               joukkueid=session.get('joukkueid'), 
                               kisaid=session.get('kisaid'), 
                               jasentenLukumaara=jasentenLukumaara)
    
    except mysql.connector.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        if con.is_connected():
            cur.close()
            con.close()

# NÄYTTÄÄ JOUKKUEEN
@views.route('/joukkue/<int:joukkueid>', methods=['GET', 'POST'])
@admin_auth 
def joukkue(joukkueid):
    from .utils import handleJoukkueenPoistaminen, handleJoukkueUpdate
    
    if not session.get('joukkueid'):
        if session.get('sarjaid'):
            return redirect(url_for('views.sarja', sarjaid=session.get('sarjaid')))
        elif session.get('kisaid'):
            return redirect(url_for('views.kilpailu', kisaid=session.get('kisaid')))
        else:
            return redirect(url_for('views.kilpailut')) 

    session['joukkueid'] = joukkueid
    
    try:
        con = create_app().pool.get_connection()
        cur = con.cursor(dictionary=True)

        # Haetaan joukkue joukkueId:n perusteella
        cur.execute("""SELECT * FROM joukkueet WHERE joukkueid = %s""", (joukkueid,))
        joukkue = cur.fetchone()

        if joukkue:
            jasenet = json.loads(joukkue['jasenet'])
            session['joukkueNimi'] = joukkue['nimi']
        else:
            jasenet = []

        # haetaan sarja johon tämä joukkue kuuluu
        sarja_id = joukkue['sarja'] if joukkue else None

        # Haetaan kilpailuId johon sarja kuuluu
        cur.execute("""SELECT kilpailu FROM sarjat WHERE sarjaid = %s""", (sarja_id,))
        kilpailu_id = cur.fetchone()['kilpailu'] if sarja_id else None

        # Haetaan kaikki sarjat
        cur.execute("""SELECT * FROM sarjat WHERE kilpailu = %s""", (kilpailu_id,))
        sarjat = cur.fetchall()

        # Post requesti
        if request.method == "POST":
            if 'delete_joukkue' in request.form:
                result = handleJoukkueenPoistaminen(con, cur)

                # Virheen sattuessa, palauta sama sivu error messagen kanssa
                if result["error_message"]:
                    return render_template(
                        "adminJoukkueTiedot.html", joukkue=joukkue, sarjat=sarjat, jasenet=jasenet, error_message=result["error_message"])
                
                return redirect(url_for('views.sarja', sarjaid=session.get('sarjaid')))
            else:
                # Päivitetään joukkue apufunktion avulla
                result = handleJoukkueUpdate(request, con, cur, joukkueid)

                if result["error_message"]:
                    return render_template(
                        "adminJoukkueTiedot.html", joukkue=joukkue, sarjat=sarjat, jasenet=jasenet, error_message=result["error_message"])

                # Haetaan päivitetyn joukkueen tiedot
                cur.execute("""SELECT * FROM joukkueet WHERE joukkueid = %s""", (joukkueid,))
                joukkue = cur.fetchone()
                jasenet = json.loads(joukkue['jasenet']) if joukkue['jasenet'] else []

                # Palataan pääsivulle onnistuneen päivityksen jälkeen
                return render_template(
                    "adminJoukkueTiedot.html", joukkue=joukkue, sarjat=sarjat, jasenet=jasenet)

        # Get pyynnössä renderöidään joukkuetiedot
        return render_template(
            "adminJoukkueTiedot.html", joukkue=joukkue, sarjat=sarjat, jasenet=jasenet)

    except mysql.connector.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {str(e)}", status=500)

    finally:
        if con.is_connected():
            cur.close()
            con.close()


@views.route('/tiedot', methods=['GET', 'POST'])
@auth
def tiedot():
    from .utils import handleJoukkueUpdate
    try:
        # Haetaan kilpailun tiedot sessiosta
        joukkueid = session.get('joukkueid')
        kilpailu_nimi = session.get('kilpailu_nimi')
        kilpailu_pvm = session.get('kilpailu_pvm').strftime('%Y-%m-%d')
        kilpailuid = session.get('valittuKilpailuId')

        con = create_app().pool.get_connection()
        cur = con.cursor(dictionary = True)

        # Haetaan joukkueen tiedot
        cur.execute("""
            SELECT nimi, salasana, sarja, jasenet
            FROM joukkueet
            WHERE joukkueid = %s
        """, (joukkueid,))
        joukkue = cur.fetchone()

        # Muunnetaan jäsenet listaksi
        jasenet_list = json.loads(joukkue['jasenet']) if joukkue['jasenet'] else []

        # Haetaan sarjat kilpailusta
        cur.execute('SELECT * FROM sarjat WHERE kilpailu = %s', (kilpailuid,))
        sarjat = cur.fetchall()

        # Handle POST requests
        if request.method == "POST":
            result = handleJoukkueUpdate(request, con, cur, joukkueid)
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
            return redirect(url_for("views.joukkueet"))

        # renderöidään joukkuetiedot sivu
        return render_template(
            "joukkuetiedot.html",
            kilpailu_nimi=kilpailu_nimi,
            kilpailu_pvm=kilpailu_pvm,
            joukkue=joukkue,
            sarjat=sarjat,
            jasenet=jasenet_list,
        )

    except mysql.connector.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui virhe: {repr(e)}", status=500)

    finally:
        if con.is_connected():
            cur.close()
            con.close()
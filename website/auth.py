from flask import Blueprint, Response, render_template, redirect, url_for, session, request
import mysql
from website import create_app
from .auth_utils import get_competitions_with_year, authenticate_team, set_session_variables

auth = Blueprint('auth', __name__)

@auth.route('/kirjaudu', methods=['GET', 'POST'])
def kirjaudu():    
    try:
        # Luodaan yhteys tietokantaan
        con = create_app().pool.get_connection()
        cur = con.cursor(dictionary=True)

        # Haetaan kilpailut vuosilukuineen
        kilpailutjaVuosi = get_competitions_with_year(cur)
        
        if request.method == "POST":
            tunnus = request.form.get("tunnus")
            salasana = request.form.get("salasana")
            valittuKilpailuId = request.form.get("kilpailu")

            if not tunnus or not salasana or not valittuKilpailuId:
                error_message = "valitse kilpailu ja syötä tunnus sekä salasana"
                return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi, error_message=error_message)

            # Autentikoidaan kilpialu ja katsotaan onko salasana oikein
            is_authenticated, message = authenticate_team(cur, tunnus, salasana, valittuKilpailuId)

            if is_authenticated:
                # Asetetaan sessionit kirjautuneelle joukkueelle
                set_session_variables(cur, session, message, valittuKilpailuId, tunnus)
                return redirect(url_for('views.joukkueet'))
            else:
                return render_template("auth.kirjaudu.html", kilpailut=kilpailutjaVuosi, error_message=message)
        
        # Get requesti, renderöidään sivu uudelleen
        return render_template("kirjaudu.html", kilpailut=kilpailutjaVuosi)

    except mysql.connector.Error as e:
        return Response(f"Tietokanta ei aukene: {str(e)}", status=500)
    except Exception as e:
        return Response(f"Tapahtui he virhe: {str(e)}", status=500)

    finally:
        if con.is_connected():
            cur.close()
            con.close()


@auth.route('/admin', methods=['GET', 'POST'])
def admin():
    from .utils import hashPassword
    if request.method == "POST":
        tunnus = request.form.get("tunnus")
        salasana = request.form.get("salasana")   
        error_message = ""
        
        if not tunnus or not salasana:
            error_message = "Syötä tunnus ja salasana"
            return render_template("kirjauduAdmin.html", error_message=error_message)

        # Salasanan hashaus
        avain = u"jokujokuavain"
        salasana = hashPassword(avain, salasana)    
        
        
        if tunnus == "admin" and salasana == '96d3cf4d4fe8e5ea39207038ce45a89a37b985c5f85dd4af9d68629c2895caaa947cab7bf9ba570883b14684476ed7d0208f6eaec079d34d1a486b672e472cc9':
            session['adminKirjautunut'] = "ok"
            return redirect(url_for('views.kilpailut'))  # Redirect to competition page
        else:
            error_message = "väärä tunnus tai salasana"
            return render_template("kirjauduAdmin.html", error_message=error_message)
            
    return render_template("kirjauduAdmin.html")


@auth.route('/logout', methods=['POST'])
def logout():    
    isAdmin = session.get('adminKirjautunut')
    session.clear()
    
    if isAdmin == "ok":
        return redirect(url_for('auth.admin'))
    else:
        return redirect(url_for('auth.kirjaudu'))


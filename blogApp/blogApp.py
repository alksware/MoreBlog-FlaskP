from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps




#url den erişimi engelleme
def loginRequied(func):
    @wraps(func)
    def validateLogin(*args, **kwargs):
        if "logged_in" in session:
            return func(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın","danger")
            return redirect(url_for("login"))
    return validateLogin


class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.length(min=4, max=25)])
    username = StringField("Kullanıcı Adı", validators=[validators.length(min=5, max=30)])
    email = StringField("Email Adresi", validators=[validators.Email(message="Lütfen geçerli bir email adresi girin")])
    password = PasswordField("Parola", validators=[validators.DataRequired(message="Lütfen bir parola belirleyin"),
                                                   validators.EqualTo(fieldname="confirm", message="Parola uyuşmuyor")])
    confirm = PasswordField("Parola Doğrula")
  
#validators bize çeşitli doğrulama imkanları verir

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

app = Flask(__name__)
app.secret_key = "ybblog"
#mysql configurasyon
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():
    number = [1,2,3,4,5]
    articles = [
    {"id": 1, "title": "das kapital", "content": "politican"},
    {"id": 2, "title": "mein kopf", "content": "politican"},
    {"id": 3, "title": "the world bigger than five", "content": "politican"}
    ]


    return render_template("index.html",answer = "evet", numbers = number, articles = articles )

# dinamik url tanımlama
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    query = "select * from articles where id = %s"
    result = cursor.execute(query, (id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article=article)
    else:
        flash("Makale Bulunamadı","danger")
        return render_template("article.html", article= None)
    


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/articles")
@loginRequied
def articles():
    cursor = mysql.connection.cursor()
    query = "select * from articles"
    result = cursor.execute(query)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        flash("Hiç makalen yok neden birkaç tane eklemiyorsun","danger")
        return render_template("articles.html")

# get veya post request alıp alabildiğimizi belirtiyoruz
@app.route("/register",methods = ["GET","POST"])
def register():
    #formunun içindeki tüm bilgileri postluyoruz
    # Bu kısım, Flask web uygulamanızda bir HTML formunun WTForms formuna dönüştürüldüğü yerdir.
    # RegisterForm adlı bir WTForms formunu, HTTP isteğinden gelen form verileriyle oluşturmak için kullanılır.
    form = RegisterForm(request.form)

    #Bu ifade, gelen HTTP isteğinin bir POST isteği olup olmadığını kontrol eder.
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()
        query = "INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)"
        cursor.execute(query, (name, email, username, password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla Kayıt oluşturuldu...", "success")

        # post edildiğinde yönlendirdiği sayfa
        # form gönderilmişse, kullanıcıyı "index" adlı bir sayfaya yönlendirir.
        return redirect(url_for("login"))
    else:
       return render_template("register.html", form = form)

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password = form.password.data
        cursor = mysql.connection.cursor()
        query = "select * from users where username = %s"
        result = cursor.execute(query, (username,))

        if result > 0:
            data = cursor.fetchone()
            realPassword = data["password"]
            if sha256_crypt.verify(password,realPassword):
                flash("Başarıyla Giriş Yapıldı","success")
                #session başlatıldı
                session["logged_in"] = True
                session["username"] = username


                return redirect(url_for("index"))
            else:
                flash("Parolanızı Yanlış Girdiğniz","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunmuyor", "danger")
            return redirect(url_for("login"))
    return render_template("login.html", form = form)    

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/dashboard")
@loginRequied
def dashboard():
    cursor = mysql.connection.cursor()
    query = "select * from articles where author = %s"
    result = cursor.execute(query,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        flash("Hiç makalen yok neden bir tane eklemiyorsun?","warning")
        render_template("dashboard.html")
    

    return render_template("dashboard.html")

@app.route("/addArticle", methods = ["GET","POST"])
@loginRequied
def addArticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        author = session["username"]
        title = form.title.data
        content = form.content.data
        
        cursor = mysql.connection.cursor()
        query = "INSERT INTO articles(author, title, content) VALUES(%s, %s, %s)"
        cursor.execute(query, (author,title,content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Oluşturuldu", "success")
        print("{} posted a new article to {}".format(session["username"],app.config["MYSQL_DB"]))
        return redirect(url_for("dashboard"))

    return render_template("addArticle.html",form = form)

@app.route("/delete/<string:id>")	
@loginRequied
def delete(id):
    cursor = mysql.connection.cursor()
    query = "select * from articles where author = %s and id = %s "
    result = cursor.execute(query,(session["username"],id))
    if result > 0:
        deleteQuery = "delete from articles where id = %s"
        cursor.execute(deleteQuery,(id,))
        mysql.connection.commit()
        return redirect(url_for("dashboard"))
    else:
        flash("Bu makaleyi silemezsiniz","danger")
        return redirect(url_for("index"))

@app.route("/edit/<string:id>", methods = ["GET","POST"])
@loginRequied
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        query = "select * from articles where id = %s and author = %s"
        result = cursor.execute(query,(id,session["username"]))
        if result == 0:
            flash("İşlem yapılamadı","danger")
            return redirect(url_for("index"))
        else:
            # article varsa...
            article = cursor.fetchone()
            form = ArticleForm()
            # form a article daki mevcut bilgileri doldurduk
            form.title.data =  article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form = form)

    else:
        # post request
        form = ArticleForm(request.form)
        updatedTitle = form.title.data
        updatedContent = form.content.data
        cursor = mysql.connection.cursor()
        queryUpdate = "update articles set title = %s, content = %s where id = %s"

        cursor.execute(queryUpdate,(updatedTitle,updatedContent,id))
        mysql.connection.commit()
        flash(f"{form.title.data} adlı makale güncellendi","warning")
        return redirect(url_for("index"))


@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index.html"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        query = "select * from articles where title like '%"+keyword+"%'"
        result = cursor.execute(query)
        if result == 0:
            flash("Sonuç bulunamadı","warning")
            return  redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)


class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.length(min=5, max=100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.length(min = 150)])

if __name__ == "__main__":
    app.run(debug=True)


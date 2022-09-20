from flask import Flask, render_template, request, redirect, session
from cs50 import SQL
import ast
from flask_session import Session
from helpers import login_required, act_calculate,makeRandomList
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask("__name__")

#_________________________________Sessionのdictオブジェクトを作成__________________________________________
app.config["SESSION_PERMANENT"] = False
# セッションの保存期間を指定
app.config["SESSION_TYPE"] = "filesystem"
#　ファイルとしてflask_sessionというセッションデータベースを作成する。
Session(app)
# 作成したセッションファイルとアプリを接続
#---------------------------------------------------------------------------------------------------------

# sqliteをデータベースに接続する
db = SQL("sqlite:///foodname.db")
db1 =SQL("sqlite:///users.db")

#------------------------------
#     LOGIN機能の実装:
#------------------------------

#----------------------------------------ログイン画面(login)--------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # sessionの情報を消す
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if (request.method == "POST"):

        # Ensure username was submitted
        username = request.form.get("username")
        password = request.form.get("password")
        if not username :
            raise Exception('ユーザー名を入力してください！！！')
        if not password :
            raise Exception('パスワードを入力してください！！！')

        # Query database for username
        rows = db1.execute("SELECT * FROM users WHERE username = ?", username)

        if (check_password_hash(rows[0]["hash"], password)):

            # Remember which user has logged in
            session["user_id"] = rows[0]["id"]

            # Redirect user to home page
            return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("LOGIN/login.html")
# ---------------------------------------------------------------------------------------------------------------

# --------------------------------------登録画面(register)---------------------------------------------------
@app.route("/register",methods=["GET","POST"])
def register():
    if (request.method=="GET"):
        return render_template("main/register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username :
            raise Exception('ユーザー名を入力してください！！！')
        if not password :
            raise Exception('パスワードを入力してください！！！')
        if not confirmation:
            raise Exception('確認パスワードも入力してください！！！')

        if password != confirmation:
            raise Exception('パスワードが一致してないでよ！')

        # データの登録
        db1.execute("INSERT INTO users (username,hash) VALUES (?,?)", username, generate_password_hash(password))

        return redirect("/login")


# ------------------------------------------------------------------------------------------------------------

#______________________________________ログアウト画面(logout)__________________________________________________
@app.route("/logout")
@login_required
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")
#______________________________________________________________________________________________



# ------------------------------------ホーム画面(home)--------------------------------------------------------
@app.route("/",methods=["GET","POST"])
@login_required
def home():
    data = db.execute("SELECT * FROM foodnames")
    count = 0
    return render_template("main/home.html", data=data, count=count)
# -------------------------------------------------------------------------------------------------------------


# ------------------------------------------入力画面(input)----------------------------------------------------
@app.route("/input", methods=["GET","POST"])
@login_required
def index():
    if (request.method == "GET"):
        return render_template("main/activeLevel.html")

    else:
        if 'level' not in session:
            session['level'] = request.form.get("level")
            return render_template("main/meal.html")
        else:
            level = session['level']
            session.pop("level", None)
            pass

        # 一人当たりの必要摂取カロリー
        personal_data = db1.execute("SELECT * FROM personal_data WHERE user_id = ?", session['user_id'])[0]
        age = personal_data['age']
        weight = personal_data['weight']
        height = personal_data['height']
        sex = personal_data['sex']
        activity = personal_data['activity']


        budget = request.form.get("budget")
        act = act_calculate(sex, weight, height, age, level, activity)



# --------------------------------------------------------------------
# D = act - (朝で摂取したエネルギー + 昼で摂取したエネルギー) [kcal]
# --------------------------------------------------------------------

        total_energy = 0
        total_protein = 0
        total_lipid = 0
        total_carbohydrate = 0
        fDicts = request.form.getlist("select_food")
        for fDict in fDicts:
            Dict = ast.literal_eval(fDict)
            total_energy += abs(int(Dict['エネルギー']))
            total_protein += abs(int(Dict['たんぱく質']))
            total_lipid += abs(int(Dict['脂質']))
            total_carbohydrate += abs(int(Dict['炭水化物']))

        # 1日に必要な三大栄養素
        P = 2 * weight
        P_cal = P * 4
        F_cal = act * 0.25
        F = F_cal / 9
        CBH_cal = act - P_cal - F_cal
        CBH = CBH_cal / 4

        # 夜に必要な三大栄養素
        difP = P - total_protein
        difF = F - total_lipid
        difCBH = CBH - total_carbohydrate

        # 三大栄養素の不足分
        X = difP/P + difF/F + difCBH/CBH

        D = act - total_energy

        difData = {'カロリー': D, 'タンパク質': difP, '脂質': difF, '炭水化物': difCBH}

        data = db.execute("SELECT * FROM foodnames ORDER BY ? - (タンパク質/? + 脂質/? + 炭水化物/?) LIMIT 30", X, P, F, CBH)

        data2 = []
        for dat in data:
            data2_set = []
            data2_set.append(dat)
            difP2 = difP - dat['タンパク質']
            difF2 = difF - dat['脂質']
            difCBH2 = difCBH - dat['炭水化物']
            X2 = difP2/P + difF2/F + difCBH2/CBH
            data_element2 = db.execute("SELECT * FROM foodnames ORDER BY ? - (タンパク質/? + 脂質/? + 炭水化物/?) LIMIT 10", X2, P, F, CBH)
            for i in range(len(data_element2)):
                data2_set.append(data_element2[i])
                data2.append(data2_set)


        return render_template("main/output.html", data = data, data2 = data2, difData=difData)
# -------------------------------------------------------------------------------------------------------------


# -----------------------------入力と合致する食品の栄養情報を取得------------------------------------------------------

@app.route("/search_item", methods=["GET", "POST"])
def search_item():
    if request.method == "POST":
        breakfasts = request.form.getlist("breakfast")
        lunches = request.form.getlist("lunch")
        snacks = request.form.getlist("snack")
        sql = "SELECT * FROM 食品成分 WHERE 食品名 like ?"
        brName = []
        luName = []
        snName = []
        for breakfast in breakfasts:
            if len(breakfast) != 0:
                brName += db.execute(sql, "%" + breakfast + "%")
        for lunch in lunches:
            if len(lunch) != 0:
                luName += db.execute(sql, "%" + lunch + "%")
        for snack in snacks:
            if len(snack) != 0:
                snName += db.execute(sql, "%" + snack + "%")

        return render_template("MAIN/input.html", breakfast=brName, lunch=luName, snack=snName)

# -----------------------------------------------------------------------------------------------------------------

@app.route("/back")
def back():
    return render_template("input.html")


# -------------------------recommend--------------------------------------------------------------------------------
@app.route("/recommend", methods=["GET","POST"])
def recommend():
    if (request.method == "POST"):
        # お弁当肉系
        beef = request.form.get("beef")
        # お弁当魚系
        fish = request.form.get("fish")
        # 米飯系
        rice = request.form.get("rice")
        # 麺系
        noodle = request.form.get("noodle")

        if (beef):
            beefList = db.execute('SELECT * from foodnames WHERE カテゴリ = "お弁当肉系" ')
        else:
            beefList = []
        if (fish):
            # fishList = db.execute("SELECT * from foodnames WHERE カテゴリ = ?",fish)
            fishList = db.execute('SELECT * from foodnames WHERE カテゴリ = "おべんとう 魚系" ')
        else:
            fishList = []
        if (rice):
            riceList = db.execute("SELECT * from foodnames WHERE カテゴリ = ?",rice)
        else:
            riceList = []
        if (noodle):
            noodleList = db.execute("SELECT * from foodnames WHERE カテゴリ = ?",noodle)
        else:
            noodleList = []

        #何かしらの条件に従ってこのリストに入れていく
        selectedList = []
        # リストの連結 [{1},{2},.......{n}]となる
        for element in beefList:
            selectedList.append(element)
        for element in fishList:
            selectedList.append(element)
        for element in riceList:
            selectedList.append(element)
        for element in noodleList:
            selectedList.append(element)


        if(len(selectedList) != 0):
            indexList = makeRandomList(len(selectedList))
            recommendList = []
            for index in indexList:
                recommendList.append(selectedList[index])
            return render_template("main/recommend.html",recommendList=recommendList)
        else:
            return redirect("/")
            # print("categoryが一つもチェックされていない")




# ------------------------------------------------------------------------------------------------------------------


# -----------------------------personal_data-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route("/personal_data", methods=['GET', 'POST'])
def personal_data():
    if request.method == 'POST':
        try:
            session['age'] = int(request.form.get("age"))
            session['weight'] = int(request.form.get("weight"))
            session['height'] = int(request.form.get("height"))
            session['sex'] = request.form.get("sex")
        except:
            pass

        if request.form.get("purpose") == None:
            return render_template("main/purpose.html")
        else:
            purpose = request.form.get("purpose")


        try: #dbが格納されていない場合
            db1.execute("INSERT INTO personal_data (user_id, sex, age, weight, height, activity) VALUES (?, ?, ?, ?, ?, ?)", session['user_id'], session['sex'], session['age'], session['weight'], session['heightj'], purpose)
        except: #格納されている場合（そのときはtryでエラーでる
            db1.execute("UPDATE personal_data SET sex=?, age=?, weight=?, height=?, activity=? WHERE user_id=?", session['sex'], session['age'], session['weight'], session['height'], purpose, session['user_id'])

        return redirect("/")

    else:
        return render_template("main/personal_data.html")

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


# -------------------------favorite------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
@app.route("/favorite")
def favorite():
    if(request.method== "GET"):
        return render_template("main/favorite.html")
    else:
        # output画面からデータを受け取って、foodnamesからデータを取ってくる。
        # one~sixまでが毎回異なっていれば最高
        # one~sixの候補(その賞品を表す固有のものがいい。候補：url,id)←商品名も考えたが、ユニークでないものがあった。lx：牛カルビマヨネーズ
        one = request.form.get("one")
        two = request.form.get("two")
        three = request.form.get("three")
        four = request.form.get("four")
        five = request.form.get("five")
        six = request.form.get("six")

        if(one):
            one_name = db.execute("SELECT * FROM foodnames WHERE id = ?",one) # 候補：url,id
        else:
            one_name = [{"食品名":"sample"}]
        if(two):
            two_name = db.execute("SELECT * FROM foodnames WHERE id = ?",two)
        else:
            two_name = [{"食品名":"sample"}]
        if(three):
            three_name = db.execute("SELECT * FROM foodnames WHERE id = ?",three)
        else:
            three_name = [{"食品名":"sample"}]
        if(four):
            four_name = db.execute("SELECT * FROM foodnames WHERE id = ?",four)
        else:
            four_name = [{"食品名":"sample"}]
        if(five):
            five_name = db.execute("SELECT * FROM foodnames WHERE id = ?",five)
        else:
            five_name = [{"食品名":"sample"}]
        if(six):
            six_name = db.execute("SELECT * FROM foodnames WHERE id = ?",six)
        else:
            six_name = [{"食品名":"sample"}]

        # product_likedにまだ保存されていない商品ならという条件が必要
        identifyList = db.execute("SELECT * FROM product_liked WHERE user_id = ?", session['user_id'])
        name_list=[]
        # 初めてお気に入りを使う場合は、全てを登録する。
        if(len(identifyList)==0):
            name_list = [one_name,two_name,three_name,four_name,five_name,six_name]
            add_list = []
            for name in name_list:
                if (name[0]["食品名"] != "sample"):
                    add_list.append(name[0]["食品名"])
            for name in add_list:
                db.execute("INSERT INTO product_liked(user_id,product) VALUES(?,?)",session['user_id'],name)
        else:
            for itemDict in identifyList:
                if(one_name[0]["食品名"] != itemDict["product"]and one_name[0]["食品名"] != "sample"):
                    name_list.append(one_name[0]["食品名"])
            for itemDict in identifyList:
                if(two_name[0]["食品名"] != itemDict["product"]and two_name[0]["食品名"] != "sample"):
                    name_list.append(two_name[0]["食品名"])
            for itemDict in identifyList:
                if(three_name[0]["食品名"] != itemDict["product"]and three_name[0]["食品名"] != "sample"):
                    name_list.append(three_name[0]["食品名"])
            for itemDict in identifyList:
                if(four_name[0]["食品名"] != itemDict["product"]and four_name[0]["食品名"] != "sample"):
                    name_list.append(four_name[0]["食品名"])
            for itemDict in identifyList:
                if(five_name[0]["食品名"] != itemDict["product"]and five_name[0]["食品名"] != "sample"):
                    name_list.append(five_name[0]["食品名"])
            for itemDict in identifyList:
                if(six_name[0]["食品名"] != itemDict["product"]and six_name[0]["食品名"] != "sample"):
                    name_list.append(six_name[0]["食品名"])

            # product_likedにデータを保存する。
            if (len(name_list)!=0):
                for name in name_list:
                    db.execute("INSERT INTO product_liked(user_id,product) VALUES(?,?)",session['user_id'],name)
            else:
                # one~sixまで全てデータベースに保存されているので追加の必要がない
                pass

        # 入力されたデータを取り出してfavorite画面に送る
        product_liked_s = db.execute("SELECT product FROM product_liked WHERE user_id = ?", session['user_id'])
        submitList = []
        for product_liked in product_liked_s:
            data = db.execute("SELECT * FROM foodnames WEHRE 食品名 = ?", product_liked['product'])[0]
            submitList.append(data)
        return render_template("main/favorite.html", submitList =submitList)

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

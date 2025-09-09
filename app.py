# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.middleware.proxy_fix import ProxyFix
from sqlalchemy.orm import scoped_session, sessionmaker
from models import Base, engine, Todo
from auth import login_required, build_msal_app, build_auth_url, load_cache, save_cache
from datetime import datetime


def create_app():
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1
    )

    # Flask secret
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")

    # DB 初期化
    Base.metadata.create_all(bind=engine)
    app.db = scoped_session(sessionmaker(bind=engine))

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        app.db.remove()

    @app.route("/")
    @login_required
    def index():
        user_oid = session["user"]["oid"]
        todos = (
            app.db.query(Todo)
            .filter_by(user_oid=user_oid)
            .order_by(Todo.created_at.desc())
            .all()
        )
        return render_template("index.html", todos=todos, user=session["user"])

    @app.route("/add", methods=["POST"])
    @login_required
    def add():
        title = request.form.get("title", "").strip()
        if not title:
            flash("タスク名を入力してください。", "warning")
            return redirect(url_for("index"))
        user_oid = session["user"]["oid"]
        t = Todo(
            user_oid=user_oid, title=title, is_done=False, created_at=datetime.utcnow()
        )
        app.db.add(t)
        app.db.commit()
        return redirect(url_for("index"))

    @app.route("/toggle/<int:todo_id>", methods=["POST"])
    @login_required
    def toggle(todo_id):
        user_oid = session["user"]["oid"]
        t = app.db.query(Todo).filter_by(id=todo_id, user_oid=user_oid).first()
        if t:
            t.is_done = not t.is_done
            app.db.commit()
        return redirect(url_for("index"))

    @app.route("/delete/<int:todo_id>", methods=["POST"])
    @login_required
    def delete(todo_id):
        user_oid = session["user"]["oid"]
        t = app.db.query(Todo).filter_by(id=todo_id, user_oid=user_oid).first()
        if t:
            app.db.delete(t)
            app.db.commit()
        return redirect(url_for("index"))

    # ===== 認証フロー =====
    @app.route("/signin")
    def signin():
        session["flow"] = build_msal_app().initiate_auth_code_flow(
            scopes=os.getenv("OIDC_SCOPES", "openid profile email").split(),
            redirect_uri=os.getenv("REDIRECT_URI"),
        )
        return redirect(build_auth_url(session["flow"]))

    @app.route("/callback")
    def callback():
        cache = load_cache()
        result = build_msal_app(cache=cache).acquire_token_by_auth_code_flow(
            session.get("flow", {}), request.args
        )
        if "error" in result:
            flash(
                f"サインインに失敗しました: {result.get('error_description')}", "danger"
            )
            return redirect(url_for("index"))
        save_cache(cache)

        # id_token のクレームにユーザーの OID が含まれる
        id_claims = result.get("id_token_claims", {})
        if not id_claims.get("oid"):
            flash(
                "ユーザー識別子(oid)が取得できませんでした。アプリ登録のAPI許可を確認してください。",
                "danger",
            )
            return redirect(url_for("index"))

        session["user"] = {
            "name": id_claims.get("name") or id_claims.get("preferred_username"),
            "email": id_claims.get("preferred_username"),
            "oid": id_claims.get("oid"),
            "tid": id_claims.get("tid"),
        }
        return redirect(url_for("index"))

    @app.route("/signout")
    def signout():
        session.clear()
        # AADのサインアウト（任意）
        authority = os.getenv("AUTHORITY")
        post_logout = os.getenv("POST_LOGOUT_REDIRECT_URI", os.getenv("REDIRECT_URI"))
        return redirect(
            f"{authority}/oauth2/v2.0/logout?post_logout_redirect_uri={post_logout}"
        )

    return app


app = create_app()

if __name__ == "__main__":
    # 開発起動用
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)

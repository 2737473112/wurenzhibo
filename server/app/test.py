from flask import Flask
from models import db, UserStatus  # 确保正确导入 db 和 UserStatus

app = Flask(__name__)
# 使用与您的应用相同的配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///path/to/your/database.db'  # 替换为您的数据库路径
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    try:
        # 尝试从 UserStatus 表中获取所有记录
        user_statuses = UserStatus.query.all()
        print(f"共找到 {len(user_statuses)} 条 UserStatus 记录。")
    except Exception as e:
        print(f"查询时出现错误：{e}")

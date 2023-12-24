# routes.py

from fastapi import FastAPI, HTTPException, Depends, status,Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models import User, SpeechLibrary,QALibrary,UserStatus
from config import config
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash
from services.live_service import LiveService  # 引入LiveService类
from services.danmu_service import DanmuService  # 引入DanmuService类
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Union, Dict
import logging
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from werkzeug.security import check_password_hash
from services.live_service import LiveService  # 引入LiveService类
from services.danmu_service import DanmuService  # 引入DanmuService类
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Union
from sqlalchemy.future import select
import asyncio
from pydantic import BaseModel, Field
from typing import Optional
# 创建 FastAPI 实例
app = FastAPI()
# 设置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有域名进行跨域请求，您可以根据需要限制特定的域名
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法（GET, POST, PUT, OPTIONS 等）
    allow_headers=["*"],  # 允许所有头
)
# 配置静态文件目录
app.mount("/audio", StaticFiles(directory="/www/wwwroot/wurenzhibo/server_fastapi/audio"), name="audio")
# 创建数据库引擎
engine = create_async_engine(config.DATABASE_URL)
async_sessionmaker = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# 密码上下文
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# 模型类
class TokenData(BaseModel):
    username: str = None

class LoginModel(BaseModel):
    username: str
    password: str

class RegisterModel(BaseModel):
    username: str
    password: str

class Paragraph(BaseModel):
    main: str
    sub: List[str]

class SpeechLibraryData(BaseModel):
    paragraphs: List[Union[str, Paragraph]]

class QALibraryData(BaseModel):
    questions_answers: list[dict]  # 根据实际数据结构进行调整

 
class StartLiveRequest(BaseModel):
    voice: str
    speechSpeed: int
    broadcastStrategy: str
    aiRewrite: str

class AudioStreamRequest(BaseModel):
    current_stream_length: int

class DanmuRequest(BaseModel):
    danmu_text: str

class UserStatusResponse(BaseModel):
    user_id: int
    username: str
    is_live_streaming: bool
    is_danmaku_reply_enabled: bool
    voice: Optional[str] = Field(default=None)
    speech_speed: Optional[int] = Field(default=None)
    broadcast_strategy: Optional[str] = Field(default=None)
    ai_rewrite: bool
    is_broadcasting: bool
    current_audio_timestamp: int
    audio_playback_status: str


# 创建 JWT token
def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt

# 依赖项
async def get_db():
    async with async_sessionmaker() as db:
        yield db

# JWT 令牌验证
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> int:
    async with async_sessionmaker() as db:
        try:
            payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=["HS256"])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="Invalid token")

            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            
            if user is None:
                raise HTTPException(status_code=401, detail="User not found")
            return user.id
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")



# 全局字典来存储 live_service 实例
live_services = {}
# 全局字典来存储 DanmuService 实例
danmu_services = {}


# 登录接口
@app.post("/login")
async def login(form_data: LoginModel, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if user and check_password_hash(user.password, form_data.password):
        access_token_expires = timedelta(seconds=config.JWT_ACCESS_TOKEN_EXPIRES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(status_code=401, detail="Incorrect username or password")


@app.post("/register")
async def register(form_data: RegisterModel, db: AsyncSession = Depends(get_db)):
    # Check if the username already exists
    result = await db.execute(select(User).filter(User.username == form_data.username))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create a new user and store it in the database
    hashed_password = pwd_context.hash(form_data.password)
    new_user = User(username=form_data.username, password=hashed_password)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return {"message": "User successfully registered"}, 201


@app.post("/start_live")
async def start_live(request_data: StartLiveRequest, current_user_id: int = Depends(get_current_user)):
    async with async_sessionmaker() as db:
        try:
            # 转换 aiRewrite 从字符串到布尔值
            ai_rewrite_bool = request_data.aiRewrite == '是'
            
            # 检索语音库数据
            result = await db.execute(select(SpeechLibrary).filter(SpeechLibrary.user_id == current_user_id))
            speech_libraries = result.scalars().all()
            speech_library = speech_libraries[0].data if speech_libraries else None

            # 更新用户状态
            result = await db.execute(select(UserStatus).filter(UserStatus.user_id == current_user_id))
            user_status = result.scalar_one_or_none()
            if not user_status:
                user_status = UserStatus(
                    user_id=current_user_id,
                    is_live_streaming=False,
                    voice=request_data.voice,
                    speech_speed=request_data.speechSpeed,
                    broadcast_strategy=request_data.broadcastStrategy,
                    ai_rewrite=ai_rewrite_bool,
                    is_broadcasting=True,
                    audio_playback_status="正常"
                )
                db.add(user_status)
            else:
                user_status.is_live_streaming = False
                user_status.voice = request_data.voice
                user_status.speech_speed = request_data.speechSpeed
                user_status.broadcast_strategy = request_data.broadcastStrategy
                user_status.ai_rewrite = ai_rewrite_bool
                user_status.is_broadcasting = True
                user_status.audio_playback_status = "正常"

            # 提交更新
            await db.commit()

            # 创建直播服务实例
            live_services[current_user_id] = LiveService(
                user_id=current_user_id,
                voice=request_data.voice,
                speech_speed=request_data.speechSpeed,
                broadcast_strategy=request_data.broadcastStrategy,
                ai_rewrite=ai_rewrite_bool,
                speech_library=speech_library
            )
  
            # 检索 QA 库数据
            result = await db.execute(select(QALibrary).filter(QALibrary.user_id == current_user_id))
            qa_libraries = result.scalars().all()
            qa_library = qa_libraries[0].data if qa_libraries else None

            # 创建弹幕服务实例
            danmu_services[current_user_id] = DanmuService(
                user_id=current_user_id,
                voice=request_data.voice,
                speech_speed=request_data.speechSpeed,
                qa_library=qa_library
            )

            return {"message": "Live settings updated", "connectWebSocket": True}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Error updating live settings: {e}")


# stop_live 接口
@app.post("/stop_live")
async def stop_live(current_user_id: int = Depends(get_current_user)):
    async with async_sessionmaker() as db:
        try:
            # 查询用户状态
            result = await db.execute(select(UserStatus).filter(UserStatus.user_id == current_user_id))
            user_status = result.scalar_one_or_none()

            if user_status:
                user_status.is_live_streaming = False
                user_status.voice = None
                user_status.speech_speed = None
                user_status.broadcast_strategy = None
                user_status.ai_rewrite = False
                user_status.is_broadcasting = False

                # 提交更新
                await db.commit()

            print("停止成功")
            return {"message": "Live stopped"}
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=f"Error stopping live: {e}")

@app.post("/check_audio_stream")
async def check_audio_stream(request_data: AudioStreamRequest, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    current_stream_length = request_data.current_stream_length

    live_service = live_services.get(current_user_id)
    if live_service is None:
        raise HTTPException(status_code=404, detail="Live service not found")

    print("开始合成音频", current_stream_length)
    if current_stream_length < 5:
        audio_path = await live_service.generate_normal_audio()
        print("合成出来的音频", audio_path)
        if audio_path:
            # 返回音频文件的 URL
            audio_url = f"http://36.103.180.62:5003/{audio_path}"
            return {"audio_url": audio_url}
        else:
            raise HTTPException(status_code=500, detail="No audio generated or audio generation failed")
    elif current_stream_length >= 10:
        return {"message": "Stream length exceeds threshold, no audio generated"}

    return {"message": "Audio stream check complete"}


@app.post("/send_danmu")
async def send_danmu(request_data: DanmuRequest, db: Session = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    danmu_text = request_data.danmu_text
    if not danmu_text:
        raise HTTPException(status_code=400, detail="Missing danmu text")

    if current_user_id not in danmu_services:
        raise HTTPException(status_code=404, detail="Danmu service not initialized")

    #print("Received danmu:", danmu_text)

    try:
        danmu_service = danmu_services[current_user_id]
        audio_path = await danmu_service.generate_danmu_audio(danmu_text)  # assuming this is an async function

        if audio_path:
            # Construct the URL for the audio file
            audio_url = f"http://36.103.180.62:5003/{audio_path}"
            print("合成回复音频",audio_url)
            return {"audio_url": audio_url}
        else:
            # 当不需要生成音频或音频生成失败时，返回成功状态码但不包含音频URL
            return {"message": "Danmu received but no audio required/generated", "audio_url": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing danmu: {str(e)}")


# 异步查询所有用户状态的接口
@app.get("/all_user_statuses", response_model=List[UserStatusResponse])
async def all_user_statuses(db: AsyncSession = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    # 权限检查
    if current_user_id != 1 and current_user_id != 2:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized access")

    try:
        # 异步查询所有用户状态
        result = await db.execute(select(UserStatus, User).join(User, UserStatus.user_id == User.id))
        user_statuses = result.all()

        # 格式化数据
        statuses = [UserStatusResponse(
            user_id=user_status.user_id,
            username=user.username,
            is_live_streaming=user_status.is_live_streaming,
            is_danmaku_reply_enabled=user_status.is_danmaku_reply_enabled,
            voice=user_status.voice,
            speech_speed=user_status.speech_speed,
            broadcast_strategy=user_status.broadcast_strategy,
            ai_rewrite=user_status.ai_rewrite,
            is_broadcasting=user_status.is_broadcasting,
            current_audio_timestamp=user_status.current_audio_timestamp,
            audio_playback_status=user_status.audio_playback_status
        ) for user_status, user in user_statuses]

        return statuses
    except Exception as e:
        # 记录异常
        logging.exception(e)
        raise HTTPException(status_code=500, detail="Error retrieving user statuses")



# 更新话术库接口
@app.post("/update_speech_library")
async def update_speech_library(request: Request, db: AsyncSession = Depends(get_db), current_user_id: str = Depends(get_current_user)):
    try:
        # 解析请求数据
        data = await request.json()
        logging.info(f"Received data for update_speech_library: {data}")

        # 验证数据是否符合模型
        speech_library_data = SpeechLibraryData(**data)

        result = await db.execute(select(SpeechLibrary).filter(SpeechLibrary.user_id == current_user_id))
        speech_library = result.scalar_one_or_none()
        
        if speech_library:
            speech_library.data = speech_library_data.dict()
        else:
            speech_library = SpeechLibrary(user_id=current_user_id, data=speech_library_data.dict())
            db.add(speech_library)

        await db.commit()
        return {"message": "Speech library updated successfully"}

    except Exception as e:
        logging.error(f"Error in update_speech_library: {str(e)}")
        return {"message": f"Error processing request: {str(e)}"}, 422



# 获取话术库接口
@app.get("/get_speech_library")
async def get_speech_library(db: AsyncSession = Depends(get_db), current_user_id: str = Depends(get_current_user)):
    result = await db.execute(select(SpeechLibrary).filter(SpeechLibrary.user_id == current_user_id))
    speech_library = result.scalar_one_or_none()

    if speech_library:
        return speech_library.data
    else:
        raise HTTPException(status_code=404, detail="No speech library found for the user")


# 更新问答库接口
@app.post("/update_qa_library")
async def update_qa_library(data: QALibraryData, db: AsyncSession = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    if "questions_answers" not in data.dict():
        raise HTTPException(status_code=400, detail="Invalid data format")

    result = await db.execute(select(QALibrary).filter(QALibrary.user_id == current_user_id))
    qa_library = result.scalar_one_or_none()
    
    if qa_library:
        qa_library.data = data.dict()
    else:
        qa_library = QALibrary(user_id=current_user_id, data=data.dict())
        db.add(qa_library)

    await db.commit()
    return {"message": "QA library updated successfully"}

# 获取问答库接口
@app.get("/get_qa_library")
async def get_qa_library(db: AsyncSession = Depends(get_db), current_user_id: int = Depends(get_current_user)):
    result = await db.execute(select(QALibrary).filter(QALibrary.user_id == current_user_id))
    qa_library = result.scalar_one_or_none()
    
    if qa_library:
        return qa_library.data
    else:
        raise HTTPException(status_code=404, detail="No QA library found for the user")

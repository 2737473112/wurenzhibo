from .live_service import LiveService  # 引入LiveService类
from .danmu_service import DanmuService  # 引入DanmuService类
class ServiceFactory:
    def __init__(self):
        self.live_services = {}
        self.danmu_services = {}

    def get_live_service(self, user_id, data=None):
        if user_id not in self.live_services:
            print("开始new")
            self.live_services[user_id] = LiveService(user_id, data)
        return self.live_services[user_id]

    def get_danmu_service(self, user_id, voice=None, speech_speed=None):
        #print("实例现在的属性",)
        if user_id not in self.danmu_services:
            #print("没有userid对应的实例，创建")
            self.danmu_services[user_id] = DanmuService(user_id, voice, speech_speed)
        #print("实例现在的属性",self.danmu_services[user_id].voice)
        return self.danmu_services[user_id]
    
    def remove_live_service(self, user_id):
        if user_id in self.live_services:
            del self.live_services[user_id]

    def remove_danmu_service(self, user_id):
        if user_id in self.danmu_services:
            del self.danmu_services[user_id]

<template>
  <div>
    <h1>话术库</h1>
    <el-button type="primary" @click="addMainScript">添加主话术</el-button>
    <el-button type="primary" @click="openImportDialog">一键导入文案</el-button>
    <el-table :data="mainScripts" style="width: 100%">
      <el-table-column
        prop="paragraphs[0].main"
        label="主话术"
      ></el-table-column>
      <el-table-column label="操作">
        <template #default="scope">
          <el-button type="text" @click="openMainDialog(scope.$index)"
            >编辑主话术</el-button
          >
          <el-button type="text" @click="openSubDialog(scope.$index)"
            >编辑副话术</el-button
          >
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑主话术的 Dialog -->
    <el-dialog v-model="isMainDialogVisible" title="编辑主话术">
      <el-input
      type="textarea"
      :rows="2"
        v-if="
          currentMainScriptIndex !== null && mainScripts[currentMainScriptIndex]
        "
        v-model="mainScripts[currentMainScriptIndex].paragraphs[0].main"
        placeholder="请添加主话术"
      ></el-input>
      <!-- 可添加其他编辑主话术的内容 -->
      <el-button type="primary" @click="saveData">保存</el-button>
      <el-button @click="closeMainDialog">关闭</el-button>
      <el-button type="danger" @click="deleteMainScript">删除主话术</el-button>
    </el-dialog>

    <!-- 编辑副话术的 Dialog -->
    <el-dialog v-model="isSubDialogVisible" title="编辑副话术">
      <div
        v-for="(subScript, subIndex) in mainScripts[currentMainScriptIndex]
          .paragraphs[0].sub"
        :key="subIndex"
      >
        <el-input
        type="textarea"
        :rows="2"
          v-model="
            mainScripts[currentMainScriptIndex].paragraphs[0].sub[subIndex]
          "
          placeholder="请添加副话术"
        ></el-input>
        <el-button type="danger" @click="deleteSubScript(subIndex)"
          >删除副话术</el-button
        >
      </div>
      <el-button type="primary" @click="addSubScript">添加副话术</el-button>
      <el-button @click="saveData">保存</el-button>
      <el-button @click="closeSubDialog">关闭</el-button>
    </el-dialog>

        <!-- 导入文案的 Dialog -->
    <el-dialog v-model="isImportDialogVisible" title="导入文案">
      <el-input
        type="textarea"
        rows="5"
        v-model="importedScript"
        placeholder="请输入您的文案"
      ></el-input>
      <el-button type="primary" @click="importScripts">导入</el-button>
      <el-button @click="closeImportDialog">关闭</el-button>
    </el-dialog>

  </div>
</template>

<script>
import request from "../utils/request"; // 导入封装的 request
export default {
  name: "KnowledgeBase",
  data() {
    return {
      mainScripts: [],
      isMainDialogVisible: false,
      isSubDialogVisible: false,
      isImportDialogVisible: false,
      importedScript: "",
      currentMainScriptIndex: null,
    };
  },
  mounted() {
    // 当组件挂载完成时调用 fetchSpeechLibrary 方法
    this.fetchSpeechLibrary();
  },
  methods: {
    addMainScript() {
      this.mainScripts.push({
        paragraphs: [
          {
            main: "请添加主话术",
            sub: [],
          },
        ],
      });
    },

    // 新增方法用于获取话术库数据
    async fetchSpeechLibrary() {
      try {
        const response = await request.get("/get_speech_library");
        if (response.status === 200 && response.data) {
          // 直接将接收到的数据分配给 mainScripts
          this.mainScripts = response.data.paragraphs.map((item) => ({
            paragraphs: [item],
          }));
        } else {
          // 处理无数据或错误的情况
          console.error("获取话术库失败：" + response.data.message);
        }
      } catch (error) {
        console.error("获取话术库出错：" + error.message);
      }
    },
    saveData() {
      // 构造请求数据
      const requestData = {
        paragraphs: this.mainScripts.map((script) => ({
          main: script.paragraphs[0].main,
          sub: script.paragraphs[0].sub,
        })),
      };

      // 发送 POST 请求到后端
      request
        .post("/update_speech_library", requestData)
        .then((response) => {
          if (response.status === 200) {
            // 请求成功的处理
            console.log("话术库更新成功");
          } else {
            // 请求失败的处理
            console.error("话术库更新失败：" + response.data.message);
          }
        })
        .catch((error) => {
          // 错误处理
          console.error("话术库更新失败：" + error.response.data.message);
        });

      // 重置对话框的可见性
      this.isMainDialogVisible = false;
      this.isSubDialogVisible = false;
    },

    openMainDialog(index) {
      this.currentMainScriptIndex = index;
      this.isMainDialogVisible = true;
    },
    openSubDialog(index) {
      this.currentMainScriptIndex = index;
      this.isSubDialogVisible = true;
    },
    addSubScript() {
      this.mainScripts[this.currentMainScriptIndex].paragraphs[0].sub.push("");
    },
    closeMainDialog() {
      this.isMainDialogVisible = false;
    },
    closeSubDialog() {
      this.isSubDialogVisible = false;
    },
    deleteMainScript() {
      // 移除当前选中的主话术及其副话术
      this.mainScripts.splice(this.currentMainScriptIndex, 1);

      // 重置当前索引或进行其他必要的处理
      if (this.mainScripts.length <= this.currentMainScriptIndex) {
        this.currentMainScriptIndex = null;
      }

      // 更新后端数据
      this.saveData();

      // 关闭编辑主话术的对话框
      this.isMainDialogVisible = false;
    },
    deleteSubScript(subIndex) {
      if (this.currentMainScriptIndex !== null) {
        this.mainScripts[this.currentMainScriptIndex].paragraphs[0].sub.splice(subIndex, 1);
      }
    },

    openImportDialog() {
      this.isImportDialogVisible = true;
    },
    closeImportDialog() {
      this.isImportDialogVisible = false;
    },
    importScripts() {
      const scriptChunks = this.importedScript.match(/[\s\S]{1,300}/g) || [];
      scriptChunks.forEach(chunk => {
        this.mainScripts.push({
          paragraphs: [{ main: chunk, sub: [] }]
        });
      });

      this.saveData();
      this.closeImportDialog();
    }

  },
};
</script>
  
<style>
/* 页面的样式 */
</style>

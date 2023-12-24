<template>
  <div>
    <h1>问答库</h1>
    <el-button type="primary" @click="addQuestion">添加问题</el-button>
    <el-table :data="questions" style="width: 100%">
      <el-table-column prop="paragraphs[0].main" label="问题"></el-table-column>
      <el-table-column label="操作">
        <template #default="scope">
          <el-button type="text" @click="openQuestionDialog(scope.$index)">编辑问题</el-button>
          <el-button type="text" @click="openAnswerDialog(scope.$index)">编辑回答</el-button>
        </template>
      </el-table-column>
    </el-table>

  <!-- 编辑问题的 Dialog -->
  <el-dialog v-model="isQuestionDialogVisible" title="编辑问题">
    <el-input
      type="textarea"
      :rows="2"
      v-if="currentQuestionIndex !== null && questions[currentQuestionIndex]"
      v-model="questions[currentQuestionIndex].paragraphs[0].main"
      placeholder="请添加关键词，用空格分隔"
    ></el-input>
    <el-button type="primary" @click="saveData">保存</el-button>
    <el-button @click="closeQuestionDialog">关闭</el-button>
    <el-button type="danger" @click="deleteQuestion">删除问题</el-button>
  </el-dialog>

  <!-- 编辑回答的 Dialog -->
  <el-dialog v-model="isAnswerDialogVisible" title="编辑回答">
    <div v-for="(answer, answerIndex) in questions[currentQuestionIndex].paragraphs[0].sub" :key="answerIndex">
      <el-input
        type="textarea"
        :rows="2"
        v-model="questions[currentQuestionIndex].paragraphs[0].sub[answerIndex]"
        placeholder="请添加回答"
        style="margin-bottom: 10px"
      ></el-input>
      <el-button type="danger" @click="deleteAnswer(answerIndex)">删除回答</el-button>
    </div>
    <el-button type="primary" @click="addAnswer">添加回答</el-button>
    <el-button @click="saveData">保存</el-button>
    <el-button @click="closeAnswerDialog">关闭</el-button>
  </el-dialog>
  </div>
</template>
  
<script>
import request from "../utils/request"; // 导入封装的 request
export default {
  name: "Qabase",
  data() {
    return {
      questions: [],
      isQuestionDialogVisible: false,
      isAnswerDialogVisible: false,
      currentQuestionIndex: null,
      currentAnswerIndex: null,
    };
  },
  mounted() {
    this.fetchQAData();
  },
  methods: {
    addQuestion() {
      this.questions.push({
        paragraphs: [
          {
            main: "请添加关键词，用空格分隔",
            sub: [],
          },
        ],
      });
    },

    async fetchQAData() {
      try {
        const response = await request.get("/get_qa_library");
        if (response.status === 200 && response.data) {
          // 将接收到的数据分配给 questions，每个问题包含在一个 paragraphs 结构中
          this.questions = response.data.questions_answers.map((qa) => ({
            paragraphs: [
              {
                main: qa.main,
                sub: qa.sub,
              },
            ],
          }));
        } else {
          // 处理无数据或错误的情况
          console.error("获取问答库失败：" + response.data.message);
        }
      } catch (error) {
        console.error("获取问答库出错：" + error.message);
      }
    },
    saveData() {
      // 构造请求数据，确保每个问题和答案都被封装在 paragraphs 数组中
      const requestData = {
        questions_answers: this.questions.map((question) => ({
          main: question.paragraphs[0].main,
          sub: question.paragraphs[0].sub,
        })),
      };

      // 发送 POST 请求到后端
      request
        .post("/update_qa_library", requestData)
        .then((response) => {
          if (response.status === 200) {
            // 请求成功的处理
            console.log("问答库更新成功");
          } else {
            // 请求失败的处理
            console.error("问答库更新失败：" + response.data.message);
          }
        })
        .catch((error) => {
          // 错误处理
          console.error("问答库更新失败：" + error.response.data.message);
        });

      // 重置对话框的可见性
      this.isAnswerDialogVisible = false;
      this.isQuestionDialogVisible = false;
    },

    openQuestionDialog(index) {
      this.currentQuestionIndex = index;
      this.isQuestionDialogVisible = true;
    },
    openAnswerDialog(index) {
      this.currentQuestionIndex = index;
      this.isAnswerDialogVisible = true;
    },
    addAnswer() {
      if (
        this.currentQuestionIndex !== null &&
        this.questions[this.currentQuestionIndex]
      ) {
        const question =
          this.questions[this.currentQuestionIndex].paragraphs[0];
        if (Array.isArray(question.sub)) {
          question.sub.push("");
        } else {
          // 如果 sub 不是一个数组，则初始化为一个空数组并添加一个空字符串
          question.sub = [""];
        }
      } else {
        console.error("无效的问题索引：", this.currentQuestionIndex);
      }
    },
    closeQuestionDialog() {
      this.isQuestionDialogVisible = false;
    },
    closeAnswerDialog() {
      this.isAnswerDialogVisible = false;
    },

    deleteQuestion() {
      // 删除当前选中的问题
      this.questions.splice(this.currentQuestionIndex, 1);
      // 处理索引和后续逻辑
      this.currentQuestionIndex = null;
      this.saveData();
      this.closeQuestionDialog();
    },
    deleteAnswer(answerIndex) {
      // 删除当前问题下的特定回答
      if (this.currentQuestionIndex !== null) {
        this.questions[this.currentQuestionIndex].paragraphs[0].sub.splice(answerIndex, 1);
      }
      // 可能需要在此处调用 saveData 方法来保存更改
    },

  },
};
</script>
  
<style>
/* 页面的样式 */
</style>
  
# Frontend

IHRS 前端项目，基于 Vue 3 + Vite + Element Plus。

## 当前功能

- 首页展示
- 后台管理页面
- 医院管理
- 诊室管理
- 医生管理
- 新增、编辑、删除、详情查看
- 多选删除
- 页面刷新后保留当前后台页面状态

## 技术栈

- Vue 3
- Vite
- Element Plus

## 启动方式

```bash
cd frontend
npm install
npm run dev
```

默认访问地址：

```text
http://localhost:5173
```

## 构建

```bash
npm run build
```

## 目录说明

```text
src/
├── App.vue        # 页面主入口
├── main.js        # 应用挂载
└── styles.css     # 全局样式
```

## 说明

当前后台管理页面中的医院、诊室、医生数据仍以前端本地状态为主，后续建议改为对接后端接口和数据库。

# IHRS

智能医院挂号系统（Intelligent Hospital Registration System）。

当前项目采用前后端分离与独立 Agent 服务架构：
- `frontend`：Vue 3 + Element Plus，负责首页、后台管理页面
- `backend`：Spring Boot 3，负责业务接口、数据持久化
- `agent-service`：FastAPI，负责 AI 导诊能力预留
- `deploy`：Docker Compose、环境变量与部署配置

## 当前进度

### 前端
- 已完成首页与后台管理页面
- 已支持医院、诊室、医生三类资源管理
- 已支持新增、编辑、删除、查看详情
- 已支持多选删除
- 已支持刷新后保留当前页面与后台模块

### 后端
- 已完成 Spring Boot 基础工程
- 已接入 MySQL、Redis、RabbitMQ 配置
- 已提供健康检查接口
- 已建立医院、诊室、医生三类 JPA 实体与 Repository

### 数据库
- 使用 MySQL 8.4
- 已建立三张核心表：
  - `hospital`
  - `clinic_room`
  - `doctor`
- 已建立关联关系与级联删除约束

### Agent
- 已提供 `agent-service` 骨架
- 当前 `/consult` 仍为占位实现，后续适合接入 LangChain

## 项目结构

```text
.
├── frontend/        # Vue 3 前端
├── backend/         # Spring Boot 后端
├── agent-service/   # Python FastAPI Agent 服务
├── deploy/          # Docker Compose 和环境配置
└── 文档.md
```

## 环境要求

- Node.js 18+
- Java 17
- Docker / Docker Compose

## 快速启动

### 1. 配置环境变量

复制配置文件：

```bash
cp deploy/.env.example deploy/.env
```

根据实际情况修改：
- MySQL 账号密码
- 大模型服务地址与密钥

### 2. 使用 Docker 启动整套服务

```bash
cd deploy
docker compose up --build
```

默认端口：
- 前端：`http://localhost:5173`
- 后端：`http://localhost:8080`
- Agent：`http://localhost:8000`
- MySQL：`localhost:3306`
- RabbitMQ 管理台：`http://localhost:15672`

## 单独开发启动

### 前端

```bash
cd frontend
npm install
npm run dev
```

### 后端

请确保本机使用 Java 17，并保证 MySQL 已启动。

```bash
cd backend
mvn spring-boot:run
```

### Agent

```bash
cd agent-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 数据库说明

数据库连接配置来自：
- [deploy/.env](deploy/.env)
- [backend/src/main/resources/application.yml](backend/src/main/resources/application.yml)

核心表结构：
- `hospital`：医院信息
- `clinic_room`：诊室信息，关联 `hospital`
- `doctor`：医生信息，关联 `hospital` 与 `clinic_room`

后端在 `spring.jpa.hibernate.ddl-auto=update` 下启动时，会自动同步表结构。

## 现阶段适合的 AI 方案

结合当前架构，更推荐：
- `backend` 继续负责业务和数据
- `agent-service` 使用 `LangChain` 承担 AI 导诊、科室推荐、医生推荐

不建议把核心 AI 编排重新塞回 Spring Boot。

## 后续可继续完善

- 后端补全医院、诊室、医生 CRUD 接口
- 前端接入真实后端数据
- Agent 接入 LangChain 与知识库检索
- 增加登录、权限、预约挂号流程

# IHRS

智能医院挂号系统（Intelligent Hospital Registration System）。

IHRS 是一个面向患者与医院管理人员的全栈示例项目，覆盖 AI 导诊、挂号预约、用户登录、后台管理和 Docker 一键部署等完整链路。当前仓库已经包含前端、业务后端、独立 AI 服务以及 MySQL / Redis / RabbitMQ 的容器化运行方案，适合课程设计、毕设展示、全栈练手和二次开发。

## 项目亮点

- 面向普通用户与管理员的双角色系统
- 支持手机号注册、登录、会话鉴权与权限隔离
- 支持 AI 导诊并将推荐结果带入预约流程
- 支持医院、诊室、医生、预约四大后台管理模块
- 支持医生排班、时段限额、重复预约校验
- 支持首页查看“我的预约”并直接取消预约
- 支持未来 15 天号源展示与预约容量查询
- 支持 Docker Compose 一键启动完整环境

## 功能概览

### 1. 用户与权限

- 普通用户可注册并登录系统
- 管理员可通过内置账号登录后台
- Redis 用于存储登录会话
- 普通用户只能使用：
  - 首页
  - AI 问诊
  - 挂号预约
- 管理员额外可访问：
  - 医院管理
  - 诊室管理
  - 医生管理
  - 预约管理

### 2. AI 问诊

- 前端提供独立 AI 问诊入口
- 用户输入症状后，可得到推荐科室、医院、诊室和医生
- 当前默认实现为规则匹配 / 占位式导诊逻辑
- `agent-service` 已预留对接真实大模型的扩展入口

说明：

- 当前结果仅用于导诊演示，不构成医疗诊断建议
- 可进一步接入 OpenAI、通义、DeepSeek 或 LangChain

### 3. 挂号预约

- 用户按“医院 -> 诊室 -> 日期 -> 医生 -> 填信息”的流程完成预约
- 日期选择展示未来 15 天预约情况
- 支持查看日期维度剩余号源和可约医生数
- 支持查询医生指定日期 / 时段余号
- 支持取消预约
- 首页“我的预约”仅展示状态为“已预约”的有效记录

### 4. 后台管理

当前后台已支持以下数据模块：

- 医院管理
- 诊室管理
- 医生管理
- 预约管理

每个模块具备的核心能力：

- 列表展示
- 搜索与筛选
- 查看详情
- 新增
- 编辑
- 删除
- 批量删除

### 5. 关键业务规则

- 普通用户必须登录后才能创建预约
- 同一医生同一天同一时段最多预约 `10` 人
- 同一普通用户不能重复预约同一医生的同一天同一时段
- 已取消预约不计入时段容量
- 同一诊室同一时段不能安排两位医生同时出诊
- 用户只能预约医生实际排班时段

## 技术架构

### 前端

- Vue 3
- Vite
- Element Plus

### 后端

- Spring Boot 3
- Spring Web
- Spring Data JPA
- Spring Validation
- MySQL
- Redis
- RabbitMQ

### AI 服务

- FastAPI
- Uvicorn
- Pydantic

### 部署

- Docker
- Docker Compose
- Nginx

## 项目结构

```text
.
├── frontend/                  # Vue 3 前端应用
├── backend/                   # Spring Boot 后端服务
├── agent-service/             # FastAPI AI 导诊服务
├── deploy/                    # Docker Compose 与环境配置
├── README.md
└── ...
```

## 运行环境

推荐直接使用 Docker 方式启动。

### Docker 运行所需

- Docker
- Docker Compose

### 本地分服务开发所需

- Node.js 20+
- Java 17
- Maven 3.9+
- Python 3.11+
- MySQL 8+
- Redis 7+
- RabbitMQ 3.13+

## 快速开始

### 方式一：Docker Compose 一键启动

这是当前最推荐的方式。

```bash
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up --build -d
```

查看服务状态：

```bash
docker compose -f deploy/docker-compose.yml ps
```

停止服务：

```bash
docker compose -f deploy/docker-compose.yml down
```

默认访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8080`
- AI 服务：`http://127.0.0.1:8000`
- RabbitMQ 管理台：`http://127.0.0.1:15672`

### 方式二：本地分服务启动

#### 1. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:5173
```

#### 2. 启动后端

启动前请确保 MySQL、Redis、RabbitMQ 已可用。

```bash
cd backend
mvn spring-boot:run
```

默认地址：

```text
http://127.0.0.1:8080
```

#### 3. 启动 AI 服务

```bash
cd agent-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

默认地址：

```text
http://127.0.0.1:8000
```

## 环境变量说明

Docker 启动默认读取 `deploy/.env`。

当前常用变量包括：

- `FRONTEND_PORT`：前端暴露端口
- `BACKEND_PORT`：后端暴露端口
- `AGENT_PORT`：AI 服务端口
- `MYSQL_DATABASE`：MySQL 数据库名
- `MYSQL_ROOT_PASSWORD`：MySQL root 密码
- `MYSQL_USERNAME`：业务数据库用户名
- `MYSQL_PASSWORD`：业务数据库密码
- `REDIS_PORT`：Redis 端口
- `RABBITMQ_PORT`：RabbitMQ 端口
- `RABBITMQ_MANAGEMENT_PORT`：RabbitMQ 管理台端口
- `LLM_BASE_URL`：外部大模型兼容接口地址
- `LLM_API_KEY`：外部大模型密钥
- `LLM_MODEL`：外部大模型名称

说明：

- 如果你准备公开仓库，建议立即替换或移除当前环境文件中的真实密钥
- 生产环境请不要直接使用仓库中的默认密码和默认端口

## 默认账号

### 管理员账号

- 手机号：`13800000000`
- 密码：`040130`

说明：

- 管理员密码可通过后端环境变量 `ADMIN_PASSWORD` 覆盖
- 普通注册入口不会创建管理员账号

## 数据存储说明

### MySQL

核心业务数据存储在 MySQL 中，包括：

- 医院
- 诊室
- 医生
- 预约记录
- 用户账号

当前核心表：

- `hospital`
- `clinic_room`
- `doctor`
- `appointment`
- `user_account`

后端默认使用：

```yaml
spring.jpa.hibernate.ddl-auto: update
```

应用启动时会自动同步表结构。

### 数据表注释

项目内已加入数据库注释初始化器：

- 启动后会自动为核心表写入表注释
- 同时会为字段写入列注释
- 当前仅在 MySQL 环境下执行

相关代码位于：

- `backend/src/main/java/com/ihrs/backend/config/DatabaseCommentInitializer.java`

### Redis

Redis 当前主要用于登录会话管理：

- 登录成功后生成 token
- 以 `ihrs:session:<token>` 的形式保存会话
- 后端基于 Redis 校验登录态与角色信息

### RabbitMQ

RabbitMQ 当前已接入部署和基础配置，后续可以扩展为：

- 预约通知
- 异步任务解耦
- 导诊任务排队处理

## API 概览

### 认证接口

- `POST /api/auth/register`：普通用户注册
- `POST /api/auth/login`：登录
- `POST /api/auth/logout`：退出登录
- `GET /api/auth/me`：获取当前登录用户

### 公开目录接口

- `GET /api/catalog/hospitals`
- `GET /api/catalog/rooms`
- `GET /api/catalog/doctors`

### 预约接口

- `POST /api/appointments`：创建预约
- `GET /api/appointments`：查询当前用户预约
- `PUT /api/appointments/{id}/cancel`：取消当前用户预约
- `GET /api/appointments/quota`：查询指定医生某日某时段余号
- `GET /api/appointments/quota-calendar`：查询日期范围内可预约日历数据

### 后台管理接口

- `GET /api/admin/hospitals`
- `POST /api/admin/hospitals`
- `PUT /api/admin/hospitals/{id}`
- `DELETE /api/admin/hospitals/{id}`

- `GET /api/admin/rooms`
- `POST /api/admin/rooms`
- `PUT /api/admin/rooms/{id}`
- `DELETE /api/admin/rooms/{id}`

- `GET /api/admin/doctors`
- `POST /api/admin/doctors`
- `PUT /api/admin/doctors/{id}`
- `DELETE /api/admin/doctors/{id}`

- `GET /api/admin/appointments`
- `PUT /api/admin/appointments/{id}/cancel`
- `DELETE /api/admin/appointments/{id}`

### 健康检查接口

- 后端：`GET /actuator/health`
- AI 服务：`GET /health`

## Docker 说明

当前 `deploy/docker-compose.yml` 包含以下服务：

- `frontend`
- `backend`
- `agent-service`
- `mysql`
- `redis`
- `rabbitmq`

代理关系如下：

- 前端容器通过 Nginx 对后端和 AI 服务做反向代理
- 前端访问 `/api/*` 时转发到后端
- 前端访问 `/agent/*` 时转发到 AI 服务

## 当前代码特点

- 前端主页面目前集中在 `frontend/src/App.vue`
- 样式主要集中在 `frontend/src/styles.css`
- 后端当前使用自定义拦截器完成鉴权，而非完整 Spring Security
- Vite 构建时会有 chunk size warning，但不影响当前运行

## 已实现的用户体验改进

- 首页支持快速查看“我的预约”
- 首页可直接取消有效预约
- 已取消预约不会继续出现在首页预约列表中
- 预约页支持未来 15 天日期卡片展示
- 预约页支持日期取消选择和医生延迟展示
- 首页和预约页的文案与信息层级已做过多轮简化

## 后续可继续完善

- 接入真实大模型问诊
- 引入 RAG / 知识库检索
- 将 `App.vue` 拆分为更清晰的组件结构
- 增加单元测试、接口测试和端到端测试
- 增加短信 / 邮件通知
- 增加管理员统计图表
- 增加预约记录导出能力

## 注意事项

- AI 导诊结果仅供参考，不构成正式医疗建议
- 当前仓库未单独声明开源许可证
- 如需公开发布，建议补充 `LICENSE` 并清理敏感配置

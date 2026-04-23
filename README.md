# IHRS

智能医院挂号系统（Intelligent Hospital Registration System）。

这是一个面向患者与医院管理人员的全栈项目，包含前端页面、业务后端、AI 导诊服务，以及基于 Docker Compose 的一键部署方案。当前版本已经打通了登录鉴权、AI 导诊、挂号预约、后台管理、医生排班与预约容量控制等核心链路。

## 项目简介

IHRS 旨在提供一套完整的医院预约与导诊系统，覆盖以下典型场景：

- 普通用户使用手机号和密码登录
- 普通用户通过 AI 问诊获取推荐科室、医院、诊室和医生
- 普通用户按医生时段完成挂号预约
- 管理员维护医院、诊室、医生和预约数据
- 系统根据医生排班和时段容量限制控制可预约资源

## 当前已实现功能

### 1. 用户与权限

- 首页支持用户切换
- 支持手机号 + 密码登录
- 支持普通用户注册
- 系统内置唯一管理员账号
- 普通用户只能访问：
  - `AI 问诊`
  - `挂号预约`
- 管理员才能访问：
  - `后台管理`
  - 全部医院 / 诊室 / 医生 / 预约管理功能

### 2. AI 问诊

- 前端提供独立 AI 问诊页面
- 用户输入症状后，Agent 服务返回初步导诊建议
- 当前导诊逻辑为规则匹配版
- 已支持根据症状推荐：
  - 科室
  - 医院
  - 诊室
  - 医生
- 用户可从 AI 推荐结果直接跳转到预约页

说明：

- 当前尚未接入真实外部大模型
- `agent-service` 已预留为后续接入 OpenAI / DeepSeek / 通义 / LangChain 的入口

### 3. 挂号预约

- 支持选择医院、诊室、医生、日期、时段进行预约
- 支持展示当前医生该时段剩余号源
- 每位医生在同一天同一时段最多预约 `10` 人
- 同一普通用户不能重复预约同一位医生的同一天同一时段
- 医生预约名片会根据当前用户的预约情况显示：
  - `预约`
  - `已预约`
- 预约记录支持取消

### 4. 后台管理

后台管理页面已支持以下模块：

- 医院管理
- 诊室管理
- 医生管理
- 预约管理

每个模块当前支持：

- 列表展示
- 搜索
- 筛选
- 查看详情
- 新增
- 编辑
- 删除
- 批量删除

### 5. 医生排班规则

- 医生具有固定工作时间段 `workTimeSlot`
- 同一个诊室的同一个时间段不能同时安排两位医生上班
- 用户预约时只能选择该时段真正上班的医生

### 6. 页面导航体验

- 已处理浏览器返回按钮导致直接退出页面的问题
- 当前前端使用 URL 查询参数维护页面状态，例如：
  - `?view=consult`
  - `?view=appointment`
  - `?view=admin&module=doctor`

## 技术架构

### 前端

- Vue 3
- Vite
- Element Plus

### 后端

- Spring Boot 3.4.5
- Spring Web
- Spring Data JPA
- Spring Validation
- MySQL
- Redis
- RabbitMQ

### Agent 服务

- FastAPI
- Python 3.11

### 部署

- Docker
- Docker Compose
- Nginx（前端容器内）

## 项目结构

```text
.
├── frontend/        # Vue 3 前端应用
├── backend/         # Spring Boot 业务后端
├── agent-service/   # FastAPI AI 导诊服务
├── deploy/          # Docker Compose 部署配置
└── README.md
```

## 运行环境

推荐环境：

- Docker
- Docker Compose

如需本地分服务开发，还需要：

- Node.js 20+
- Java 17
- Python 3.11
- Maven 3.9+
- MySQL 8+
- Redis 7+
- RabbitMQ 3.13+

## 快速启动

### 方式一：使用 Docker 启动整套项目

这是当前最推荐的启动方式。

```bash
cd deploy
docker compose up --build -d
```

启动后默认访问地址：

- 前端：`http://127.0.0.1:5173`
- 后端：`http://127.0.0.1:8080`
- Agent：`http://127.0.0.1:8000`
- MySQL：`127.0.0.1:3306`
- Redis：`127.0.0.1:6379`
- RabbitMQ：`127.0.0.1:5672`
- RabbitMQ 管理台：`http://127.0.0.1:15672`

查看容器状态：

```bash
docker compose -f deploy/docker-compose.yml ps
```

停止服务：

```bash
docker compose -f deploy/docker-compose.yml down
```

## 本地开发启动

### 1. 前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：

```text
http://127.0.0.1:5173
```

### 2. 后端

请先确保 MySQL、Redis、RabbitMQ 可用。

```bash
cd backend
mvn spring-boot:run
```

默认地址：

```text
http://127.0.0.1:8080
```

### 3. Agent 服务

```bash
cd agent-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

默认地址：

```text
http://127.0.0.1:8000
```

## 默认账号

### 管理员账号

- 手机号：`13800000000`
- 密码：`admin123456`

说明：

- 管理员账号只有一个
- 普通注册入口不能创建管理员

## 数据存储说明

### MySQL

业务主数据存储在 MySQL 中，包括：

- 医院
- 诊室
- 医生
- 预约记录
- 普通用户账号

当前核心表包括：

- `hospital`
- `clinic_room`
- `doctor`
- `appointment`
- `user_account`

后端使用：

```yaml
spring.jpa.hibernate.ddl-auto: update
```

应用启动时会自动同步表结构。

### Redis

Redis 当前已实际用于登录会话存储。

主要用途：

- 登录成功后生成 token
- 以 `ihrs:session:<token>` 的形式写入 Redis
- 后端接口通过 Redis 校验登录状态
- 后端根据 Redis 中的用户身份判断是否为管理员

说明：

- 当前 Redis 主要用于鉴权会话
- 医院、诊室、医生、预约等业务主数据仍然存储在 MySQL 中

### RabbitMQ

RabbitMQ 当前已接入容器与配置，但业务上暂未深度使用，后续可扩展为：

- 异步预约通知
- 消息队列解耦
- 导诊任务异步化

## 关键业务规则

### 预约规则

- 普通用户必须登录后才能预约
- 同一个医生同一天同一时段最多预约 `10` 人
- 同一个普通用户只能预约同一个医生同一天同一时段一次
- 已取消预约不计入时段容量

### 医生排班规则

- 医生必须具备工作时间段
- 同一诊室同一时间段不能存在两位医生同时排班

### 权限规则

- 未登录用户不能访问预约和后台管理接口
- 普通用户不能访问 `/api/admin/**`
- 管理员拥有全部管理权限

## 前后端接口说明

### 认证相关

- `POST /api/auth/register`：普通用户注册
- `POST /api/auth/login`：登录
- `POST /api/auth/logout`：退出登录
- `GET /api/auth/me`：获取当前登录状态

### 公开资源

- `GET /api/catalog/hospitals`
- `GET /api/catalog/rooms`
- `GET /api/catalog/doctors`

### 预约相关

- `POST /api/appointments`
- `GET /api/appointments`
- `PUT /api/appointments/{id}/cancel`
- `GET /api/appointments/quota`

### 后台管理

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

### 健康检查

- `GET /api/health`
- `GET /health`（agent-service）

## Docker 说明

当前 `deploy/docker-compose.yml` 包含以下服务：

- `frontend`
- `backend`
- `agent-service`
- `mysql`
- `redis`
- `rabbitmq`

其中：

- 前端容器通过 Nginx 反向代理后端和 Agent 服务
- 前端 `/api/*` 会转发到后端
- 前端 `/agent/*` 会转发到 `agent-service`

## 当前 AI 能力现状

当前 AI 导诊为规则匹配版，适合作为第一阶段演示和前后端联调基础。

现阶段优点：

- 无需外部模型服务即可运行
- 可以稳定演示从问诊到推荐再到预约的完整链路
- 便于后续无缝替换成真实大模型

下一步推荐升级方向：

- 接入真实大模型 API
- 增加提示词模板
- 增加结构化推荐结果
- 引入向量检索和知识库
- 根据医生详情和专长做更精细匹配

## 已知说明

- 当前 AI 导诊结果仅供辅助参考，不构成医疗诊断
- 当前前端主页面集中在 `frontend/src/App.vue`
- 当前后端使用自定义拦截器做鉴权，尚未引入完整 Spring Security
- 当前前端构建产物体积较大，Vite build 会提示 chunk size warning，但不影响运行

## 后续可继续完善

- 接入真实大模型问诊
- 增加预约记录“我的预约”独立页面
- 增加短信通知 / 邮件通知
- 增加医生出诊日历
- 增加管理员统计报表
- 增加单元测试与接口测试
- 将前端页面拆分为多个 Vue 组件，降低 `App.vue` 复杂度

## License

当前仓库未单独声明开源许可证。如需开源发布，建议补充 `LICENSE` 文件。

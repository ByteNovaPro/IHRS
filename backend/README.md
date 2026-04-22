# Backend

IHRS 后端项目，基于 Spring Boot 3。

## 当前功能

- Spring Boot 基础服务
- 健康检查接口
- MySQL 数据源配置
- Redis / RabbitMQ 基础配置
- 医院、诊室、医生三类实体与 Repository

## 技术栈

- Spring Boot 3.4.5
- Spring Web
- Spring Data JPA
- MySQL
- Redis
- RabbitMQ
- Lombok

## 启动前要求

- Java 17
- MySQL 已启动

## 本地启动

```bash
cd backend
mvn spring-boot:run
```

服务默认端口：

```text
http://localhost:8080
```

## 当前包结构

```text
src/main/java/com/ihrs/backend/
├── controller/
├── entity/
├── repository/
└── IhrsBackendApplication.java
```

## 数据库表

当前已对应以下三张核心表：
- `hospital`
- `clinic_room`
- `doctor`

实体文件：
- [Hospital.java](src/main/java/com/ihrs/backend/entity/Hospital.java)
- [ClinicRoom.java](src/main/java/com/ihrs/backend/entity/ClinicRoom.java)
- [Doctor.java](src/main/java/com/ihrs/backend/entity/Doctor.java)

当应用启动且数据库可连接时，JPA 会自动更新表结构。

## 后续建议

- 增加医院、诊室、医生 CRUD Controller / Service
- 增加 DTO、参数校验和统一异常处理
- 与前端后台管理页面完成联调

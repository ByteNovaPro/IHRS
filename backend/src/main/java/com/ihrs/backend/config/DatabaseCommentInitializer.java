package com.ihrs.backend.config;

import java.sql.Connection;
import java.sql.DatabaseMetaData;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.Map;
import javax.sql.DataSource;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Component
public class DatabaseCommentInitializer implements ApplicationRunner {

    private final JdbcTemplate jdbcTemplate;
    private final DataSource dataSource;

    public DatabaseCommentInitializer(JdbcTemplate jdbcTemplate, DataSource dataSource) {
        this.jdbcTemplate = jdbcTemplate;
        this.dataSource = dataSource;
    }

    @Override
    public void run(ApplicationArguments args) throws Exception {
        if (!isMySql()) {
            return;
        }

        String schemaName = jdbcTemplate.queryForObject("SELECT DATABASE()", String.class);
        if (schemaName == null || schemaName.isBlank()) {
            return;
        }

        for (Map.Entry<String, String> tableEntry : tableComments().entrySet()) {
            applyTableComment(tableEntry.getKey(), tableEntry.getValue());
        }

        for (Map.Entry<String, Map<String, String>> tableEntry : columnComments().entrySet()) {
            for (Map.Entry<String, String> columnEntry : tableEntry.getValue().entrySet()) {
                applyColumnComment(schemaName, tableEntry.getKey(), columnEntry.getKey(), columnEntry.getValue());
            }
        }
    }

    private boolean isMySql() throws SQLException {
        try (Connection connection = dataSource.getConnection()) {
            DatabaseMetaData metaData = connection.getMetaData();
            String productName = metaData.getDatabaseProductName();
            return productName != null && productName.toLowerCase().contains("mysql");
        }
    }

    private void applyTableComment(String tableName, String comment) {
        String sql = "ALTER TABLE `" + tableName + "` COMMENT = '" + escapeSql(comment) + "'";
        jdbcTemplate.execute(sql);
    }

    private void applyColumnComment(String schemaName, String tableName, String columnName, String comment) {
        ColumnDefinition definition = jdbcTemplate.query(
            """
            SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA, DATA_TYPE
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? AND COLUMN_NAME = ?
            """,
            rs -> rs.next()
                ? new ColumnDefinition(
                    rs.getString("COLUMN_TYPE"),
                    "YES".equalsIgnoreCase(rs.getString("IS_NULLABLE")),
                    rs.getString("COLUMN_DEFAULT"),
                    rs.getString("EXTRA"),
                    rs.getString("DATA_TYPE")
                )
                : null,
            schemaName,
            tableName,
            columnName
        );

        if (definition == null) {
            return;
        }

        StringBuilder sql = new StringBuilder();
        sql.append("ALTER TABLE `").append(tableName).append("` MODIFY COLUMN `").append(columnName).append("` ");
        sql.append(definition.columnType()).append(" ");
        sql.append(definition.nullable() ? "NULL" : "NOT NULL");

        String defaultClause = buildDefaultClause(definition);
        if (!defaultClause.isBlank()) {
            sql.append(defaultClause);
        }

        String extraClause = buildExtraClause(definition.extra());
        if (!extraClause.isBlank()) {
            sql.append(" ").append(extraClause);
        }

        sql.append(" COMMENT '").append(escapeSql(comment)).append("'");
        jdbcTemplate.execute(sql.toString());
    }

    private String buildDefaultClause(ColumnDefinition definition) {
        if (definition.defaultValue() == null || containsIgnoreCase(definition.extra(), "auto_increment")) {
            return "";
        }

        String normalizedDefault = definition.defaultValue();
        if ("current_timestamp()".equalsIgnoreCase(normalizedDefault) || "current_timestamp".equalsIgnoreCase(normalizedDefault)) {
            return " DEFAULT CURRENT_TIMESTAMP";
        }

        if (isQuotedDefaultType(definition.dataType())) {
            return " DEFAULT '" + escapeSql(normalizedDefault) + "'";
        }

        return " DEFAULT " + normalizedDefault;
    }

    private String buildExtraClause(String extra) {
        if (extra == null || extra.isBlank()) {
            return "";
        }

        return extra.replace("DEFAULT_GENERATED", "").trim().replaceAll("\\s+", " ");
    }

    private boolean isQuotedDefaultType(String dataType) {
        return switch (dataType == null ? "" : dataType.toLowerCase()) {
            case "char", "varchar", "text", "tinytext", "mediumtext", "longtext",
                 "date", "datetime", "timestamp", "time", "year" -> true;
            default -> false;
        };
    }

    private String escapeSql(String value) {
        return value.replace("'", "''");
    }

    private boolean containsIgnoreCase(String source, String target) {
        return source != null && source.toLowerCase().contains(target.toLowerCase());
    }

    private Map<String, String> tableComments() {
        Map<String, String> comments = new LinkedHashMap<>();
        comments.put("hospital", "医院基础信息表");
        comments.put("clinic_room", "诊室信息表");
        comments.put("doctor", "医生排班与介绍信息表");
        comments.put("appointment", "挂号预约记录表");
        comments.put("user_account", "系统用户账号表");
        return comments;
    }

    private Map<String, Map<String, String>> columnComments() {
        Map<String, Map<String, String>> comments = new LinkedHashMap<>();

        Map<String, String> hospital = new LinkedHashMap<>();
        hospital.put("id", "医院主键ID");
        hospital.put("name", "医院名称");
        hospital.put("level", "医院等级");
        hospital.put("location", "医院地址");
        hospital.put("short_intro", "医院简介");
        hospital.put("detail_intro", "医院详细介绍");
        hospital.put("created_at", "创建时间");
        hospital.put("updated_at", "更新时间");
        comments.put("hospital", hospital);

        Map<String, String> clinicRoom = new LinkedHashMap<>();
        clinicRoom.put("id", "诊室主键ID");
        clinicRoom.put("hospital_id", "所属医院ID");
        clinicRoom.put("name", "诊室名称");
        clinicRoom.put("floor", "诊室楼层位置");
        clinicRoom.put("short_intro", "诊室简介");
        clinicRoom.put("detail_intro", "诊室详细介绍");
        clinicRoom.put("created_at", "创建时间");
        clinicRoom.put("updated_at", "更新时间");
        comments.put("clinic_room", clinicRoom);

        Map<String, String> doctor = new LinkedHashMap<>();
        doctor.put("id", "医生主键ID");
        doctor.put("hospital_id", "所属医院ID");
        doctor.put("room_id", "所属诊室ID");
        doctor.put("name", "医生姓名");
        doctor.put("title", "医生职称");
        doctor.put("specialty", "医生擅长方向");
        doctor.put("work_time_slot", "出诊时间段");
        doctor.put("short_intro", "医生简介");
        doctor.put("detail_intro", "医生详细介绍");
        doctor.put("created_at", "创建时间");
        doctor.put("updated_at", "更新时间");
        comments.put("doctor", doctor);

        Map<String, String> appointment = new LinkedHashMap<>();
        appointment.put("id", "预约记录主键ID");
        appointment.put("hospital_id", "预约医院ID");
        appointment.put("room_id", "预约诊室ID");
        appointment.put("doctor_id", "预约医生ID");
        appointment.put("user_id", "关联用户ID");
        appointment.put("patient_name", "就诊人姓名");
        appointment.put("patient_phone", "就诊人手机号");
        appointment.put("appointment_date", "预约日期");
        appointment.put("time_slot", "预约时段");
        appointment.put("status", "预约状态");
        appointment.put("symptom", "症状描述");
        appointment.put("created_at", "创建时间");
        appointment.put("updated_at", "更新时间");
        comments.put("appointment", appointment);

        Map<String, String> userAccount = new LinkedHashMap<>();
        userAccount.put("id", "用户主键ID");
        userAccount.put("phone", "登录手机号");
        userAccount.put("password_hash", "密码哈希值");
        userAccount.put("name", "用户姓名");
        userAccount.put("role", "用户角色");
        userAccount.put("created_at", "创建时间");
        userAccount.put("updated_at", "更新时间");
        comments.put("user_account", userAccount);

        return comments;
    }

    private record ColumnDefinition(
        String columnType,
        boolean nullable,
        String defaultValue,
        String extra,
        String dataType
    ) {
    }
}

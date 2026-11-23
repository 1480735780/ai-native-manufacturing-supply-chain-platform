-- ============================================================
-- 企业配置改造：新增「企业状态」独立表 ba_com_sta
-- 目标：企业状态不再长期借用客户状态表 ba_kehuzhuangtai
-- 说明：
--   1. 本脚本用于已有数据库升级；全新安装请见 zowms.sql 中的建表语句。
--   2. 表结构与 ba_classfl / ba_com_type / ba_com_deg 保持一致（含审计列）。
--   3. 字段 com_sta_code / com_sta_name / com_sta_del 与
--      StatusFileController 导出模板中的英文表头一致。
-- ============================================================

CREATE TABLE IF NOT EXISTS `ba_com_sta` (
  `id` varchar(36) NOT NULL COMMENT '唯一id',
  `create_name` varchar(50) DEFAULT NULL COMMENT '创建人名称',
  `create_by` varchar(50) DEFAULT NULL COMMENT '创建人登录名称',
  `create_date` datetime DEFAULT NULL COMMENT '创建日期',
  `update_name` varchar(50) DEFAULT NULL COMMENT '更新人名称',
  `update_by` varchar(50) DEFAULT NULL COMMENT '更新人登录名称',
  `update_date` datetime DEFAULT NULL COMMENT '更新日期',
  `sys_org_code` varchar(50) DEFAULT NULL COMMENT '所属部门',
  `sys_company_code` varchar(50) DEFAULT NULL COMMENT '所属公司',
  `com_sta_code` varchar(32) DEFAULT NULL COMMENT '企业状态代码',
  `com_sta_name` varchar(32) DEFAULT NULL COMMENT '企业状态名称',
  `com_sta_del` varchar(1) DEFAULT NULL COMMENT '停用(Y/N)',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='企业状态';

-- 可选：如需将旧客户状态表中借用的数据迁移过来，取消下面语句注释。
-- 注意：ba_kehuzhuangtai 是「客户状态（计费方式）」表，其中混用了企业状态数据，
--       迁移前请先由业务确认哪些记录属于企业状态，避免把客户计费方式一起搬过来。
-- INSERT INTO `ba_com_sta`
--   (`id`, `com_sta_code`, `com_sta_name`, `com_sta_del`, `create_date`)
-- SELECT
--   `id`, `kehuzhuangtai_code`, `kehuzhuangtai_name`, `cus_sta_del`, `create_date`
-- FROM `ba_kehuzhuangtai`
-- WHERE `kehuzhuangtai_code` LIKE 'ENT%';

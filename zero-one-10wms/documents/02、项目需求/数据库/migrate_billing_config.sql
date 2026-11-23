-- =====================================================================
-- 计费配置模块 数据前置脚本（幂等，可重复执行）
-- 适用库：zo_wms（MySQL 8.0）
--
-- 背景：
--   1) 版本计划「计费配置」共 64 项功能，其中「客户计费方式」需要"停用"标记，
--      官方建表脚本 zowms.sql 中 ba_kehuzhuangtai 已含 cus_sta_del 字段，
--      但线上/测试库由更早版本脚本初始化，缺失该字段，需补齐。
--   2) 「仓储费率」需要独立存储表 wm_cost_conf，该表在 zowms.sql 中被注释掉，
--      实际库中不存在，需按设计重建。
--   3) 4 个字典表初始为空，补一批演示/联调用基础数据（按主键去重，重复执行安全）。
-- =====================================================================

-- ---------------------------------------------------------------------
-- 一、ba_kehuzhuangtai 补 cus_sta_del（停用）字段
-- ---------------------------------------------------------------------
SET @exist := (SELECT COUNT(*) FROM information_schema.COLUMNS
               WHERE TABLE_SCHEMA = DATABASE()
                 AND TABLE_NAME = 'ba_kehuzhuangtai'
                 AND COLUMN_NAME = 'cus_sta_del');
SET @ddl := IF(@exist = 0,
    'ALTER TABLE `ba_kehuzhuangtai` ADD COLUMN `cus_sta_del` varchar(1) NULL DEFAULT NULL COMMENT ''停用'' AFTER `kehuzhuangtai_name`',
    'DO 0');
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ---------------------------------------------------------------------
-- 二、创建 wm_cost_conf（仓储费率）
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `wm_cost_conf` (
  `id` varchar(36) CHARACTER SET utf8 COLLATE utf8_general_ci NOT NULL,
  `create_name` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '创建人名称',
  `create_by` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '创建人登录名称',
  `create_date` datetime NULL DEFAULT NULL COMMENT '创建日期',
  `update_name` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '更新人名称',
  `update_by` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '更新人登录名称',
  `update_date` datetime NULL DEFAULT NULL COMMENT '更新日期',
  `sys_org_code` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '所属部门',
  `sys_company_code` varchar(50) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '所属公司',
  `cost_code` varchar(32) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '费用名称',
  `cost_yj` varchar(32) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '价格',
  `cost_zk` varchar(32) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '折扣',
  `cost_sl` varchar(32) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '税率',
  `cost_bhs` varchar(32) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '不含税价',
  `cost_hsj` varchar(32) CHARACTER SET utf8 COLLATE utf8_general_ci NULL DEFAULT NULL COMMENT '含税价',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_wm_cost_conf_code` (`cost_code`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci COMMENT = '仓储费率' ROW_FORMAT = DYNAMIC;

-- ---------------------------------------------------------------------
-- 三、基础数据（按主键去重）
-- ---------------------------------------------------------------------
-- 3.1 客户计费方式 ba_kehuzhuangtai
INSERT INTO `ba_kehuzhuangtai`
  (`id`,`create_name`,`create_by`,`create_date`,`sys_org_code`,`sys_company_code`,`kehuzhuangtai_code`,`kehuzhuangtai_name`,`cus_sta_del`)
SELECT * FROM (
  SELECT 'seed-khzt-01' AS a,'管理员' AS b,'admin' AS c,NOW() AS d,'A05' AS e,'A05' AS f,'01' AS g,'按天计费' AS h,'0' AS i
  UNION ALL SELECT 'seed-khzt-02','管理员','admin',NOW(),'A05','A05','02','按克计费','0'
  UNION ALL SELECT 'seed-khzt-03','管理员','admin',NOW(),'A05','A05','03','按吨计费','0'
  UNION ALL SELECT 'seed-khzt-04','管理员','admin',NOW(),'A05','A05','04','按托盘计费','0'
) t WHERE NOT EXISTS (SELECT 1 FROM `ba_kehuzhuangtai` x WHERE x.`id` = t.a);

-- 3.2 计量类型 ba_pronut_type
INSERT INTO `ba_pronut_type`
  (`id`,`create_name`,`create_by`,`create_date`,`sys_org_code`,`sys_company_code`,`pronut_type_code`,`pronut_type_name`)
SELECT * FROM (
  SELECT 'seed-plx-01' AS a,'管理员' AS b,'admin' AS c,NOW() AS d,'A05' AS e,'A05' AS f,'1' AS g,'吨' AS h
  UNION ALL SELECT 'seed-plx-02','管理员','admin',NOW(),'A05','A05','2','千克'
  UNION ALL SELECT 'seed-plx-03','管理员','admin',NOW(),'A05','A05','3','立方米'
  UNION ALL SELECT 'seed-plx-04','管理员','admin',NOW(),'A05','A05','4','件'
  UNION ALL SELECT 'seed-plx-05','管理员','admin',NOW(),'A05','A05','5','托盘'
) t WHERE NOT EXISTS (SELECT 1 FROM `ba_pronut_type` x WHERE x.`id` = t.a);

-- 3.3 价格类型 ba_price_type
INSERT INTO `ba_price_type`
  (`id`,`create_name`,`create_by`,`create_date`,`sys_org_code`,`sys_company_code`,`price_type_code`,`price_type_name`)
SELECT * FROM (
  SELECT 'seed-jglx-01' AS a,'管理员' AS b,'admin' AS c,NOW() AS d,'A05' AS e,'A05' AS f,'01' AS g,'标准价' AS h
  UNION ALL SELECT 'seed-jglx-02','管理员','admin',NOW(),'A05','A05','02','协议价'
  UNION ALL SELECT 'seed-jglx-03','管理员','admin',NOW(),'A05','A05','03','促销价'
  UNION ALL SELECT 'seed-jglx-04','管理员','admin',NOW(),'A05','A05','04','阶梯价'
) t WHERE NOT EXISTS (SELECT 1 FROM `ba_price_type` x WHERE x.`id` = t.a);

-- 3.4 费用模板 ba_cost_conf
INSERT INTO `ba_cost_conf`
  (`id`,`create_name`,`create_by`,`create_date`,`sys_org_code`,`sys_company_code`,
   `cost_code`,`cost_jg`,`cost_sl`,`cost_zk`,`cost_bhs`,`cost_hs`,`free_day`,`free_day2`)
SELECT * FROM (
  SELECT 'seed-fymb-01' AS a,'管理员' AS b,'admin' AS c,NOW() AS d,'A05' AS e,'A05' AS f,
         '仓储费' AS g,'10.00' AS h,'6' AS i,'1' AS j,'9.43' AS k,'10.00' AS l,'0' AS m,'30' AS n
  UNION ALL SELECT 'seed-fymb-02','管理员','admin',NOW(),'A05','A05','装卸费','5.00','6','1','4.72','5.00','0','0'
  UNION ALL SELECT 'seed-fymb-03','管理员','admin',NOW(),'A05','A05','搬运费','3.00','6','1','2.83','3.00','0','0'
  UNION ALL SELECT 'seed-fymb-04','管理员','admin',NOW(),'A05','A05','管理费','1.50','6','1','1.42','1.50','0','0'
) t WHERE NOT EXISTS (SELECT 1 FROM `ba_cost_conf` x WHERE x.`id` = t.a);

-- 3.5 仓储费率 wm_cost_conf
INSERT INTO `wm_cost_conf`
  (`id`,`create_name`,`create_by`,`create_date`,`sys_org_code`,`sys_company_code`,
   `cost_code`,`cost_yj`,`cost_zk`,`cost_sl`,`cost_bhs`,`cost_hsj`)
SELECT * FROM (
  SELECT 'seed-ccfl-01' AS a,'管理员' AS b,'admin' AS c,NOW() AS d,'A05' AS e,'A05' AS f,
         '仓储费' AS g,'10.00' AS h,'1' AS i,'6' AS j,'9.43' AS k,'10.00' AS l
  UNION ALL SELECT 'seed-ccfl-02','管理员','admin',NOW(),'A05','A05','装卸费','5.00','1','6','4.72','5.00'
  UNION ALL SELECT 'seed-ccfl-03','管理员','admin',NOW(),'A05','A05','搬运费','3.00','1','6','2.83','3.00'
  UNION ALL SELECT 'seed-ccfl-04','管理员','admin',NOW(),'A05','A05','管理费','1.50','1','6','1.42','1.50'
) t WHERE NOT EXISTS (SELECT 1 FROM `wm_cost_conf` x WHERE x.`id` = t.a);

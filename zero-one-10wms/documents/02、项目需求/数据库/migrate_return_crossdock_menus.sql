-- ============================================================
-- 退货管理 / 越库管理 菜单初始化脚本
-- 说明：
--   1. 当前系统运行时 t_s_function 表为空，前端登录后 get-menus 返回空列表，
--      会自动回退到「前端路由 meta 生成菜单」模式（src/layouts/default.vue），
--      此时无需本脚本，页面路由 /return-management/* 与 /crossdocking-management/* 已自动生效。
--   2. 若后续启用了后端菜单管理模式（t_s_function 表有数据），执行本脚本
--      可将退货管理、越库管理两组菜单注册进系统；需将角色ID替换为实际值。
--   3. functionurl 与前端 unplugin-vue-router 文件式路由的路径一一对应。
-- ============================================================
USE `zo_wms`;

SET NAMES utf8mb4;

-- ----------------------------
-- 退货管理（一级菜单）
-- ----------------------------
INSERT INTO `t_s_function` (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`, `functionurl`, `parentfunctionid`, `functiontype`)
VALUES ('rfmgr0000000000000000000000001', NULL, 1, '退货管理', '35', '/return-management', NULL, 1);

-- 二级菜单
INSERT INTO `t_s_function` (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`, `functionurl`, `parentfunctionid`, `functiontype`)
VALUES ('rfmgr0000000000000000000000002', NULL, 2, '退货预约', '1', '/return-management/return-appointment', 'rfmgr0000000000000000000000001', 1);

INSERT INTO `t_s_function` (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`, `functionurl`, `parentfunctionid`, `functiontype`)
VALUES ('rfmgr0000000000000000000000003', NULL, 2, '客户退货', '2', '/return-management/customer-return', 'rfmgr0000000000000000000000001', 1);

INSERT INTO `t_s_function` (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`, `functionurl`, `parentfunctionid`, `functiontype`)
VALUES ('rfmgr0000000000000000000000004', NULL, 2, '退货验收', '3', '/return-management/return-acceptance', 'rfmgr0000000000000000000000001', 1);

INSERT INTO `t_s_function` (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`, `functionurl`, `parentfunctionid`, `functiontype`)
VALUES ('rfmgr0000000000000000000000005', NULL, 2, '退货上架', '4', '/return-management/return-shelving', 'rfmgr0000000000000000000000001', 1);

-- ----------------------------
-- 越库管理（一级菜单）
-- ----------------------------
INSERT INTO `t_s_function` (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`, `functionurl`, `parentfunctionid`, `functiontype`)
VALUES ('cdmgr0000000000000000000000001', NULL, 1, '越库管理', '36', '/crossdocking-management', NULL, 1);

INSERT INTO `t_s_function` (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`, `functionurl`, `parentfunctionid`, `functiontype`)
VALUES ('cdmgr0000000000000000000000002', NULL, 2, '越库订单', '1', '/crossdocking-management/crossdock-order', 'cdmgr0000000000000000000000001', 1);

-- ----------------------------
-- 角色绑定（示例：管理员角色，请按实际角色ID调整）
-- t_s_role 中管理员角色 ID 需查询确认后替换 :roleAdminId
-- ----------------------------
-- INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`) VALUES
-- ('rf00000000000000000000000000101', 'rfmgr0000000000000000000000001', :roleAdminId),
-- ('rf00000000000000000000000000102', 'rfmgr0000000000000000000000002', :roleAdminId),
-- ('rf00000000000000000000000000103', 'rfmgr0000000000000000000000003', :roleAdminId),
-- ('rf00000000000000000000000000104', 'rfmgr0000000000000000000000004', :roleAdminId),
-- ('rf00000000000000000000000000105', 'rfmgr0000000000000000000000005', :roleAdminId),
-- ('rf00000000000000000000000000106', 'cdmgr0000000000000000000000001', :roleAdminId),
-- ('rf00000000000000000000000000107', 'cdmgr0000000000000000000000002', :roleAdminId);

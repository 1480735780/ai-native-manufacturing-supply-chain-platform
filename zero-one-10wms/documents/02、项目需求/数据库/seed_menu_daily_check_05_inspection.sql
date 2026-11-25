-- 异常巡检菜单种子：MENU-DAILY-CHECK-05（/inspection/alerts）及其角色绑定
--
-- 背景：
--   前端 src/views/inspection/alerts/index.vue 由 vite-plugin-vue-router 自动生成路由
--   /inspection/alerts；侧边栏菜单来自后端 /login/get-menus（t_s_function 树），
--   页面可见性取决于当前用户角色在 t_s_role_function 中是否绑定了该菜单。
--   运行时库（2026-11-25 核对）已存在该菜单并绑 cg/ckjl/gly，但仓库内一直没有对应种子，
--   本文件把这一事实落盘，使全新环境可复现。
--
-- 【纯增量契约】（与 seed_daycheck_no_up_goods_page_role.sql 一致）
-- 1) 角色 ID 按 rolecode 动态查询，必须恰好一行；为 0 或 >1 直接 SIGNAL 中止；
-- 2) 不使用任何 DELETE：既有菜单行、既有角色绑定只增不减；
-- 3) ID 冲突（同一 function_id 指向别的 URL/名称）或 URL 冲突（同一 URL 被别的 ID 占用）→ SIGNAL 中止，
--    绝不覆盖既有映射；
-- 4) 菜单行与角色绑定均为 INSERT ... WHERE NOT EXISTS，可重复执行且幂等；
-- 5) 只绑业务角色 cg（仓管）/ ckjl（仓库经理）/ gly（管理员）；KH/cw/cs 不绑定，
--    与 Agent 侧 INSPECTION_ROLES={ckjl,cg} + ADMIN_AUTHORITIES 口径一致。
--
-- 执行方式：mysql CLI 可直接 source 本文件；程序化执行需按 DELIMITER 拆分。

USE `zo_wms`;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS `p_seed_menu_daily_check_05_inspection`;

DELIMITER //
CREATE PROCEDURE `p_seed_menu_daily_check_05_inspection`()
BEGIN
    DECLARE v_role_count INT DEFAULT 0;
    DECLARE v_role_id VARCHAR(64);
    DECLARE v_probe VARCHAR(512);
    DECLARE v_code VARCHAR(64);

    -- (1) 三个业务角色各自按 rolecode 动态取唯一 ID；不创建角色、不硬编码 ID。
    SET v_code = 'cg';
    SELECT COUNT(*) INTO v_role_count FROM `t_s_role` WHERE `rolecode` = v_code;
    IF v_role_count <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'seed aborted: expected exactly one t_s_role row with rolecode=cg';
    END IF;
    SET v_code = 'ckjl';
    SELECT COUNT(*) INTO v_role_count FROM `t_s_role` WHERE `rolecode` = v_code;
    IF v_role_count <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'seed aborted: expected exactly one t_s_role row with rolecode=ckjl';
    END IF;
    SET v_code = 'gly';
    SELECT COUNT(*) INTO v_role_count FROM `t_s_role` WHERE `rolecode` = v_code;
    IF v_role_count <> 1 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'seed aborted: expected exactly one t_s_role row with rolecode=gly';
    END IF;

    -- (3) 父菜单 MENU-DAILY-CHECK：只检测冲突，不改既有行。
    SET v_probe = NULL;
    SELECT `functionurl` INTO v_probe FROM `t_s_function` WHERE `ID` = 'MENU-DAILY-CHECK';
    IF v_probe IS NOT NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: MENU-DAILY-CHECK exists but has a functionurl (expected NULL parent)';
    END IF;

    -- (3) 子菜单 MENU-DAILY-CHECK-05：ID/URL 双向冲突检测。
    SET v_probe = NULL;
    SELECT `functionurl` INTO v_probe FROM `t_s_function` WHERE `ID` = 'MENU-DAILY-CHECK-05';
    IF v_probe IS NOT NULL AND v_probe <> '/inspection/alerts' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: MENU-DAILY-CHECK-05 already maps to a different URL';
    END IF;
    SET v_probe = NULL;
    SELECT `ID` INTO v_probe FROM `t_s_function`
        WHERE `functionurl` = '/inspection/alerts' AND `ID` <> 'MENU-DAILY-CHECK-05' LIMIT 1;
    IF v_probe IS NOT NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /inspection/alerts already mapped to a different function id';
    END IF;

    -- 父菜单行（不存在时才插入；functiontype=0 为菜单，functionurl 为 NULL）
    INSERT INTO `t_s_function`
        (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`,
         `functionurl`, `parentfunctionid`, `functiontype`)
    SELECT 'MENU-DAILY-CHECK', NULL, 1, '每日检查', '4', NULL, NULL, 0
    WHERE NOT EXISTS (SELECT 1 FROM `t_s_function` WHERE `ID` = 'MENU-DAILY-CHECK');

    -- 子菜单行（不存在时才插入；运行时库已有，此语句会被跳过，不改 functionorder 等既有字段）
    INSERT INTO `t_s_function`
        (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`,
         `functionurl`, `parentfunctionid`, `functiontype`)
    SELECT 'MENU-DAILY-CHECK-05', NULL, 2, '异常巡检', '5', '/inspection/alerts', 'MENU-DAILY-CHECK', 0
    WHERE NOT EXISTS (SELECT 1 FROM `t_s_function` WHERE `ID` = 'MENU-DAILY-CHECK-05');

    -- (5) 角色绑定：只新增缺失的绑定，保留既有其它角色不变。
    -- 菜单树按父节点构建：子菜单 05 对某角色可见，其父菜单 MENU-DAILY-CHECK 也必须对该角色可见，
    -- 否则 05 不会出现在该角色的侧边栏里（运行时库核对：父菜单原只绑 gly，导致 ckjl/cg 看不到 05）。
    -- 因此父菜单与子菜单对 cg/ckjl/gly 三个角色一并补齐绑定。
    SET v_role_id = NULL;
    SELECT `ID` INTO v_role_id FROM `t_s_role` WHERE `rolecode` = 'cg';
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-MENU-DAILY-CHECK-CG', 'MENU-DAILY-CHECK', v_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'MENU-DAILY-CHECK' AND `roleid` = v_role_id);
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-MENU-DAILY-CHECK-05-CG', 'MENU-DAILY-CHECK-05', v_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'MENU-DAILY-CHECK-05' AND `roleid` = v_role_id);

    SET v_role_id = NULL;
    SELECT `ID` INTO v_role_id FROM `t_s_role` WHERE `rolecode` = 'ckjl';
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-MENU-DAILY-CHECK-CKJL', 'MENU-DAILY-CHECK', v_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'MENU-DAILY-CHECK' AND `roleid` = v_role_id);
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-MENU-DAILY-CHECK-05-CKJL', 'MENU-DAILY-CHECK-05', v_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'MENU-DAILY-CHECK-05' AND `roleid` = v_role_id);

    SET v_role_id = NULL;
    SELECT `ID` INTO v_role_id FROM `t_s_role` WHERE `rolecode` = 'gly';
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-MENU-DAILY-CHECK-05-GLY', 'MENU-DAILY-CHECK-05', v_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'MENU-DAILY-CHECK-05' AND `roleid` = v_role_id);
END//
DELIMITER ;

CALL `p_seed_menu_daily_check_05_inspection`();
DROP PROCEDURE `p_seed_menu_daily_check_05_inspection`;

-- 巡检分页端点资源/角色映射种子（GET /daycheck/no-up/get-no-up-goods-page）
--
-- 背景：oauth2 的 ResourcesServiceImpl.loadData() 从 t_s_function(functiontype=1, functionurl IS NOT NULL)
-- 加载资源，再经 TSRoleMapper.selectRoleByFunctionUrl 连接 t_s_role_function 得到 rolecode，
-- 写入 Redis 哈希 AUTH:RESOURCE_ROLES；网关 LoadResourcesDataImpl.loadRolesByUrlPath 按 URL 读取该映射。
--
-- 【阶段0 纯增量契约】
-- 1) insp_read 角色 ID 按 rolecode 动态查询，必须恰好一行；为 0 或 >1 直接 SIGNAL 中止；
-- 2) 不使用任何 DELETE：旧端点 /daycheck/no-up/get-no-up-goods 的既有角色/权限只增不减；
-- 3) ID 冲突（同一 function_id 指向别的 URL）或 URL 冲突（同一 URL 被别的 function_id 占用）→ SIGNAL 中止，
--    绝不覆盖既有映射；
-- 4) 不触碰 MENU-DAILY-CHECK-04/05（运行时库中 05 为 /inspection/alerts 菜单，已绑 cg/ckjl/gly）；
-- 5) 资源行与角色绑定均为 INSERT ... WHERE NOT EXISTS，可重复执行且幂等。
--
-- 执行方式：mysql CLI 可直接 source 本文件；程序化执行需按 DELIMITER 拆分（见 __tests__ 说明）。

USE `zo_wms`;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS `p_seed_daycheck_no_up_page_role`;

DELIMITER //
CREATE PROCEDURE `p_seed_daycheck_no_up_page_role`()
BEGIN
    DECLARE v_role_count INT DEFAULT 0;
    DECLARE v_probe VARCHAR(512);

    -- (1) 按 rolecode 动态取唯一 insp_read 角色 ID；不创建角色、不硬编码 ID。
    SELECT COUNT(*) INTO v_role_count FROM `t_s_role` WHERE `rolecode` = 'insp_read';
    IF v_role_count <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: expected exactly one t_s_role row with rolecode=insp_read';
    END IF;
    SELECT `ID` INTO @insp_read_role_id FROM `t_s_role` WHERE `rolecode` = 'insp_read';

    -- (3) 新分页端点：ID/URL 冲突检测（冲突即中止，不覆盖）。
    SET v_probe = NULL;
    SELECT `functionurl` INTO v_probe FROM `t_s_function`
        WHERE `ID` = 'FN-DAYCHECK-NO-UP-PAGE';
    IF v_probe IS NOT NULL AND v_probe <> '/daycheck/no-up/get-no-up-goods-page' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-NO-UP-PAGE already maps to a different URL';
    END IF;
    SET v_probe = NULL;
    SELECT `ID` INTO v_probe FROM `t_s_function`
        WHERE `functionurl` = '/daycheck/no-up/get-no-up-goods-page'
          AND `ID` <> 'FN-DAYCHECK-NO-UP-PAGE' LIMIT 1;
    IF v_probe IS NOT NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: page URL already mapped to a different function id';
    END IF;

    -- (3) 旧端点：同样只检测冲突，不改既有行、不删既有绑定、不减少既有角色。
    SET v_probe = NULL;
    SELECT `functionurl` INTO v_probe FROM `t_s_function`
        WHERE `ID` = 'FN-DAYCHECK-NO-UP-LEGACY';
    IF v_probe IS NOT NULL AND v_probe <> '/daycheck/no-up/get-no-up-goods' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-NO-UP-LEGACY already maps to a different URL';
    END IF;
    SET v_probe = NULL;
    SELECT `ID` INTO v_probe FROM `t_s_function`
        WHERE `functionurl` = '/daycheck/no-up/get-no-up-goods'
          AND `ID` <> 'FN-DAYCHECK-NO-UP-LEGACY' LIMIT 1;
    IF v_probe IS NOT NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: legacy URL already mapped to a different function id';
    END IF;

    -- (5) 纯增量插入资源行（存在即跳过，不覆盖 functionname/functionorder 等既有字段）。
    INSERT INTO `t_s_function`
        (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`,
         `functionurl`, `parentfunctionid`, `functiontype`)
    SELECT 'FN-DAYCHECK-NO-UP-LEGACY', NULL, 2, '出库未上架查询', '94',
           '/daycheck/no-up/get-no-up-goods', NULL, 1
    WHERE NOT EXISTS (SELECT 1 FROM `t_s_function` WHERE `ID` = 'FN-DAYCHECK-NO-UP-LEGACY');

    INSERT INTO `t_s_function`
        (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`,
         `functionurl`, `parentfunctionid`, `functiontype`)
    SELECT 'FN-DAYCHECK-NO-UP-PAGE', NULL, 2, '出库未上架查询（巡检分页）', '95',
           '/daycheck/no-up/get-no-up-goods-page', NULL, 1
    WHERE NOT EXISTS (SELECT 1 FROM `t_s_function` WHERE `ID` = 'FN-DAYCHECK-NO-UP-PAGE');

    -- (5) 纯增量绑定 insp_read：只新增缺失的绑定，保留既有其它角色不变。
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-DAYCHECK-NO-UP-LEGACY-INSPECT', 'FN-DAYCHECK-NO-UP-LEGACY', @insp_read_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'FN-DAYCHECK-NO-UP-LEGACY' AND `roleid` = @insp_read_role_id);

    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-DAYCHECK-NO-UP-PAGE-INSPECT', 'FN-DAYCHECK-NO-UP-PAGE', @insp_read_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'FN-DAYCHECK-NO-UP-PAGE' AND `roleid` = @insp_read_role_id);
END//
DELIMITER ;

CALL `p_seed_daycheck_no_up_page_role`();
DROP PROCEDURE `p_seed_daycheck_no_up_page_role`;

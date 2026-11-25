-- 巡检积压一致快照端点资源/角色映射种子（GET /dashboard/query-pend-snapshot，阶段3）
--
-- 背景：oauth2 的 ResourcesServiceImpl.loadData() 从 t_s_function(functiontype=1, functionurl IS NOT NULL)
-- 加载资源，再经 TSRoleMapper.selectRoleByFunctionUrl 连接 t_s_role_function 得到 rolecode，
-- 写入 Redis 哈希 AUTH:RESOURCE_ROLES；网关 LoadResourcesDataImpl.loadRolesByUrlPath 按 URL 读取该映射。
-- 执行后需刷新缓存：PUT http://<oauth2-host>:10400/open/resources/cache/reload
--
-- 【纯增量契约】（与 seed_daycheck_no_up_goods_page_role.sql 同一契约）
-- 1) insp_read 角色 ID 按 rolecode 动态查询，必须恰好一行；为 0 或 >1 直接 SIGNAL 中止；
-- 2) 不使用任何 DELETE；不触碰任何 MENU-* 菜单行；
-- 3) ID 冲突（同一 function_id 指向别的 URL）或 URL 冲突（同一 URL 被别的 function_id 占用）→ SIGNAL 中止，
--    绝不覆盖既有映射；
-- 4) 资源行与角色绑定均为 INSERT ... WHERE NOT EXISTS，可重复执行且幂等。
--
-- 注意：本种子只承载端点授权（functiontype=1，不参与菜单）。旧的 query-pend-* 缓存端点不在本种子范围。
-- 执行方式：mysql CLI 可直接 source 本文件；程序化执行需按 DELIMITER 拆分（见 __tests__ 说明）。

USE `zo_wms`;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS `p_seed_dashboard_pend_snapshot_role`;

DELIMITER //
CREATE PROCEDURE `p_seed_dashboard_pend_snapshot_role`()
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

    -- (3) ID/URL 双向冲突检测（冲突即中止，不覆盖既有映射）。
    SET v_probe = NULL;
    SELECT `functionurl` INTO v_probe FROM `t_s_function`
        WHERE `ID` = 'FN-DASH-PEND-SNAPSHOT';
    IF v_probe IS NOT NULL AND v_probe <> '/dashboard/query-pend-snapshot' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: FN-DASH-PEND-SNAPSHOT already maps to a different URL';
    END IF;
    SET v_probe = NULL;
    SELECT `ID` INTO v_probe FROM `t_s_function`
        WHERE `functionurl` = '/dashboard/query-pend-snapshot'
          AND `ID` <> 'FN-DASH-PEND-SNAPSHOT' LIMIT 1;
    IF v_probe IS NOT NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: snapshot URL already mapped to a different function id';
    END IF;

    -- (4) 纯增量插入资源行（存在即跳过，不覆盖既有字段）。
    INSERT INTO `t_s_function`
        (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`,
         `functionurl`, `parentfunctionid`, `functiontype`)
    SELECT 'FN-DASH-PEND-SNAPSHOT', NULL, 2, '待处理积压一致快照（巡检）', '96',
           '/dashboard/query-pend-snapshot', NULL, 1
    WHERE NOT EXISTS (SELECT 1 FROM `t_s_function` WHERE `ID` = 'FN-DASH-PEND-SNAPSHOT');

    -- (4) 纯增量绑定 insp_read：只新增缺失的绑定，保留既有其它角色不变。
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-DASH-PEND-SNAPSHOT-INSPECT', 'FN-DASH-PEND-SNAPSHOT', @insp_read_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'FN-DASH-PEND-SNAPSHOT' AND `roleid` = @insp_read_role_id);
END//
DELIMITER ;

CALL `p_seed_dashboard_pend_snapshot_role`();
DROP PROCEDURE `p_seed_dashboard_pend_snapshot_role`;

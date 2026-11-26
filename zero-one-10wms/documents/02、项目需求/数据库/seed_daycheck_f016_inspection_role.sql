-- 阶段8 F-016 巡检端点资源/角色映射种子
--   出货异常（巡检分页）GET /daycheck/yi-chang/get-yichang-down-page
--   出货异常（旧端点）  GET /daycheck/yi-chang/get-yichang-down
--   温度巡检（现有端点）GET /daycheck/temperature/query
--
-- 背景：oauth2 的 ResourcesServiceImpl.loadData() 从 t_s_function(functiontype=1, functionurl IS NOT NULL)
-- 加载资源，再经 TSRoleMapper.selectRoleByFunctionUrl 连接 t_s_role_function 得到 rolecode，
-- 写入 Redis 哈希 AUTH:RESOURCE_ROLES；网关 LoadResourcesDataImpl.loadRolesByUrlPath 按 URL 读取该映射。
-- 刷新：PUT oauth2:10400 /open/resources/cache/reload（经网关 10001 会 404，必须直连 oauth2）。
--
-- 【纯增量契约，与 seed_daycheck_no_up_goods_page_role.sql 一致】
-- 1) insp_read 角色 ID 按 rolecode 动态查询，必须恰好一行；为 0 或 >1 直接 SIGNAL 中止；
-- 2) 不使用任何 DELETE：旧端点既有角色/权限只增不减；
-- 3) ID 冲突（同一 function_id 指向别的 URL）或 URL 冲突（同一 URL 被别的 function_id 占用）→ SIGNAL 中止，
--    绝不覆盖既有映射；若 ID/URL 已存在但 functiontype<>1（菜单/非可激活函数）也 SIGNAL 中止，
--    避免 INSERT 被跳过造成 OAuth 永远加载不到该资源的"假成功"；
-- 6) 绑定 ID 冲突（同一 RF-* ID 已绑定到别的 function URL）→ SIGNAL 中止；
-- 7) 所有 INSERT 包在事务中，任一失败由 EXIT HANDLER ROLLBACK + RESIGNAL，杜绝部分写入。
-- 4) 不改写任何 MENU-* 菜单授权：共用端点只读取页面菜单的角色绑定，不写 MENU-* 行；
-- 5) 资源行与角色绑定均为纯增量 INSERT，已存在的绑定不重复写，可重复执行且幂等；
-- 8) 端点分两类，角色集合不同（网关自 2026-11-26 起真正按 AUTH:RESOURCE_ROLES 判 403）：
--     - 仅巡检使用：/daycheck/yi-chang/get-yichang-down-page -> 只绑 insp_read；
--     - 页面与巡检共用：/daycheck/yi-chang/get-yichang-down（出货异常页 MENU-DAILY-CHECK-02）、
--       /daycheck/temperature/query（温度维护页 MENU-DAILY-CHECK-03）
--       -> 页面菜单既有授权角色 ∪ insp_read。
--     共用端点若只绑 insp_read，页面现有用户会被网关判 403。
--     页面菜单授权以后有变更时，必须重跑本种子并刷新缓存，新增的页面角色才会同步到端点。
--
-- 执行方式：mysql CLI 可直接 source 本文件；程序化执行需按 DELIMITER 拆分。
--
-- 【手动激活步骤（本文件不自动执行，init.sh 也不执行种子或缓存刷新）】
-- (a) 在目标库执行种子：mysql -h <host> -u <user> -p <db> 后执行 source documents/02、项目需求/数据库/seed_daycheck_f016_inspection_role.sql；
-- (b) 种子写入 t_s_function/t_s_role_function 后，必须直连 oauth2 调用
--     PUT http://<oauth2 host>:10400/open/resources/cache/reload 刷新 AUTH:RESOURCE_ROLES 缓存；
--     经网关 :10001 转发该路径会返回 404，不可使用网关地址；
-- (c) init.sh 只做环境/基线/测试门禁，不会执行本种子，也不会触发缓存 reload，以上两步需人工完成。

USE `zo_wms`;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS `p_seed_daycheck_f016_inspection_role`;

DELIMITER //
CREATE PROCEDURE `p_seed_daycheck_f016_inspection_role`()
BEGIN
    DECLARE v_role_count INT DEFAULT 0;
    DECLARE v_probe VARCHAR(512);
    DECLARE v_probe_type TINYINT;
    DECLARE v_exists INT DEFAULT 0;

    -- 事务安全：任何预检/插入异常都回滚全部 INSERT，再原样抛出错误，避免部分写入。
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    -- (1) 按 rolecode 动态取唯一 insp_read 角色 ID；不创建角色、不硬编码 ID。
    SELECT COUNT(*) INTO v_role_count FROM `t_s_role` WHERE `rolecode` = 'insp_read';
    IF v_role_count <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: expected exactly one t_s_role row with rolecode=insp_read';
    END IF;
    SELECT `ID` INTO @insp_read_role_id FROM `t_s_role` WHERE `rolecode` = 'insp_read';

    -- (3) 逐端点预检：先判断行是否存在，再看内容。
    --     不能用 functionurl IS NOT NULL 之类条件代替存在性判断：
    --     既有行若 functionurl / functiontype 为 NULL，旧写法会把它当成不存在
    --     而跳过校验，随后 INSERT ... WHERE NOT EXISTS 跳过插入、
    --     角色绑定照写、事务 COMMIT 成功——OAuth 只加载
    --     functiontype=1 且 URL 非空的资源，结果是种子成功但授权无效的假成功。

    -- 出货异常新分页端点：ID 已存在时必须 URL 一致且可激活。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `ID` = 'FN-DAYCHECK-YICHANG-PAGE';
    IF v_exists > 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-YICHANG-PAGE appears more than once';
    END IF;
    IF v_exists = 1 THEN
        SET v_probe = NULL;
        SET v_probe_type = NULL;
        SELECT `functionurl`, `functiontype` INTO v_probe, v_probe_type
            FROM `t_s_function` WHERE `ID` = 'FN-DAYCHECK-YICHANG-PAGE' LIMIT 1;
        IF v_probe IS NULL OR v_probe <> '/daycheck/yi-chang/get-yichang-down-page' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-YICHANG-PAGE exists but functionurl is NULL or a different URL';
        END IF;
        IF v_probe_type IS NULL OR v_probe_type <> 1 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-YICHANG-PAGE exists but functiontype is NULL or <>1 (not activatable)';
        END IF;
    END IF;

    -- 出货异常新分页端点：同一 URL 已绑定到别的 function id -> 中止，不覆盖。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/daycheck/yi-chang/get-yichang-down-page' AND `ID` <> 'FN-DAYCHECK-YICHANG-PAGE';
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /daycheck/yi-chang/get-yichang-down-page already mapped to a different function id';
    END IF;

    -- 出货异常新分页端点：该 URL 下所有行的 functiontype 必须为 1，否则 OAuth 不会加载。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/daycheck/yi-chang/get-yichang-down-page'
          AND (`functiontype` IS NULL OR `functiontype` <> 1);
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /daycheck/yi-chang/get-yichang-down-page exists but functiontype is NULL or <>1 (not activatable)';
    END IF;

    -- 出货异常旧端点：ID 已存在时必须 URL 一致且可激活。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `ID` = 'FN-DAYCHECK-YICHANG-LEGACY';
    IF v_exists > 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-YICHANG-LEGACY appears more than once';
    END IF;
    IF v_exists = 1 THEN
        SET v_probe = NULL;
        SET v_probe_type = NULL;
        SELECT `functionurl`, `functiontype` INTO v_probe, v_probe_type
            FROM `t_s_function` WHERE `ID` = 'FN-DAYCHECK-YICHANG-LEGACY' LIMIT 1;
        IF v_probe IS NULL OR v_probe <> '/daycheck/yi-chang/get-yichang-down' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-YICHANG-LEGACY exists but functionurl is NULL or a different URL';
        END IF;
        IF v_probe_type IS NULL OR v_probe_type <> 1 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-YICHANG-LEGACY exists but functiontype is NULL or <>1 (not activatable)';
        END IF;
    END IF;

    -- 出货异常旧端点：同一 URL 已绑定到别的 function id -> 中止，不覆盖。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/daycheck/yi-chang/get-yichang-down' AND `ID` <> 'FN-DAYCHECK-YICHANG-LEGACY';
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /daycheck/yi-chang/get-yichang-down already mapped to a different function id';
    END IF;

    -- 出货异常旧端点：该 URL 下所有行的 functiontype 必须为 1，否则 OAuth 不会加载。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/daycheck/yi-chang/get-yichang-down'
          AND (`functiontype` IS NULL OR `functiontype` <> 1);
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /daycheck/yi-chang/get-yichang-down exists but functiontype is NULL or <>1 (not activatable)';
    END IF;

    -- 温度巡检端点：ID 已存在时必须 URL 一致且可激活。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `ID` = 'FN-DAYCHECK-TEMPERATURE-QUERY';
    IF v_exists > 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-TEMPERATURE-QUERY appears more than once';
    END IF;
    IF v_exists = 1 THEN
        SET v_probe = NULL;
        SET v_probe_type = NULL;
        SELECT `functionurl`, `functiontype` INTO v_probe, v_probe_type
            FROM `t_s_function` WHERE `ID` = 'FN-DAYCHECK-TEMPERATURE-QUERY' LIMIT 1;
        IF v_probe IS NULL OR v_probe <> '/daycheck/temperature/query' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-TEMPERATURE-QUERY exists but functionurl is NULL or a different URL';
        END IF;
        IF v_probe_type IS NULL OR v_probe_type <> 1 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: FN-DAYCHECK-TEMPERATURE-QUERY exists but functiontype is NULL or <>1 (not activatable)';
        END IF;
    END IF;

    -- 温度巡检端点：同一 URL 已绑定到别的 function id -> 中止，不覆盖。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/daycheck/temperature/query' AND `ID` <> 'FN-DAYCHECK-TEMPERATURE-QUERY';
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /daycheck/temperature/query already mapped to a different function id';
    END IF;

    -- 温度巡检端点：该 URL 下所有行的 functiontype 必须为 1，否则 OAuth 不会加载。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `functionurl` = '/daycheck/temperature/query'
          AND (`functiontype` IS NULL OR `functiontype` <> 1);
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: /daycheck/temperature/query exists but functiontype is NULL or <>1 (not activatable)';
    END IF;

    -- (4) 预检：绑定 ID 已存在时，必须指向本端点且绑定到 insp_read。
    --     同样先判存在性：若用 functionid IS NOT NULL 代替，既有行
    --     functionid / roleid 为 NULL 时会被当成不存在而跳过校验，
    --     WHERE NOT EXISTS 再跳过插入，最终端点仍无角色映射。

    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_role_function`
        WHERE `ID` = 'RF-YC-LEGACY-INSPECT';
    IF v_exists > 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: RF-YC-LEGACY-INSPECT appears more than once';
    END IF;
    IF v_exists = 1 THEN
        SET v_probe = NULL;
        SELECT `functionid` INTO v_probe FROM `t_s_role_function`
            WHERE `ID` = 'RF-YC-LEGACY-INSPECT' LIMIT 1;
        IF v_probe IS NULL OR v_probe <> 'FN-DAYCHECK-YICHANG-LEGACY' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: RF-YC-LEGACY-INSPECT binding exists but functionid is NULL or a different function';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM `t_s_role_function`
                       WHERE `ID` = 'RF-YC-LEGACY-INSPECT' AND `roleid` = @insp_read_role_id) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: RF-YC-LEGACY-INSPECT binding exists but is not bound to rolecode=insp_read';
        END IF;
    END IF;

    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_role_function`
        WHERE `ID` = 'RF-YC-PAGE-INSPECT';
    IF v_exists > 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: RF-YC-PAGE-INSPECT appears more than once';
    END IF;
    IF v_exists = 1 THEN
        SET v_probe = NULL;
        SELECT `functionid` INTO v_probe FROM `t_s_role_function`
            WHERE `ID` = 'RF-YC-PAGE-INSPECT' LIMIT 1;
        IF v_probe IS NULL OR v_probe <> 'FN-DAYCHECK-YICHANG-PAGE' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: RF-YC-PAGE-INSPECT binding exists but functionid is NULL or a different function';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM `t_s_role_function`
                       WHERE `ID` = 'RF-YC-PAGE-INSPECT' AND `roleid` = @insp_read_role_id) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: RF-YC-PAGE-INSPECT binding exists but is not bound to rolecode=insp_read';
        END IF;
    END IF;

    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_role_function`
        WHERE `ID` = 'RF-TEMP-Q-INSPECT';
    IF v_exists > 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: RF-TEMP-Q-INSPECT appears more than once';
    END IF;
    IF v_exists = 1 THEN
        SET v_probe = NULL;
        SELECT `functionid` INTO v_probe FROM `t_s_role_function`
            WHERE `ID` = 'RF-TEMP-Q-INSPECT' LIMIT 1;
        IF v_probe IS NULL OR v_probe <> 'FN-DAYCHECK-TEMPERATURE-QUERY' THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: RF-TEMP-Q-INSPECT binding exists but functionid is NULL or a different function';
        END IF;
        IF NOT EXISTS (SELECT 1 FROM `t_s_role_function`
                       WHERE `ID` = 'RF-TEMP-Q-INSPECT' AND `roleid` = @insp_read_role_id) THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'seed aborted: RF-TEMP-Q-INSPECT binding exists but is not bound to rolecode=insp_read';
        END IF;
    END IF;

    -- (4b) 共用端点的角色集合 = 页面菜单既有授权角色 ∪ insp_read，所以页面菜单必须存在。
    --      菜单缺失时无法推导页面角色；若退化为只绑 insp_read，网关会对页面现有用户返回 403，故中止。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `ID` = 'MENU-DAILY-CHECK-02';
    IF v_exists <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: MENU-DAILY-CHECK-02 not found, page roles of /daycheck/yi-chang/get-yichang-down must be re-derived';
    END IF;

    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_function`
        WHERE `ID` = 'MENU-DAILY-CHECK-03';
    IF v_exists <> 1 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: MENU-DAILY-CHECK-03 not found, page roles of /daycheck/temperature/query must be re-derived';
    END IF;

    -- 页面角色的绑定 ID 由 rolecode 拼出：RF-YC-LEGACY-<ROLECODE> / RF-TEMP-Q-<ROLECODE>。
    -- rolecode 超过 16 个字符会超出 varchar(32)，中止而不是被截断成冲突 ID。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists
    FROM `t_s_role_function` mr
    JOIN `t_s_role` r ON r.`ID` = mr.`roleid`
    WHERE mr.`functionid` IN ('MENU-DAILY-CHECK-02', 'MENU-DAILY-CHECK-03')
      AND CHAR_LENGTH(r.`rolecode`) > 16;
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: a page role rolecode is longer than 16 characters, derived binding id would exceed varchar(32)';
    END IF;

    -- 拼出的绑定 ID 若已被占用且指向别的函数（或 functionid 为 NULL）-> 中止，不覆盖。
    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_role_function`
        WHERE `ID` LIKE 'RF-YC-LEGACY-%'
          AND (`functionid` IS NULL OR `functionid` <> 'FN-DAYCHECK-YICHANG-LEGACY');
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: an RF-YC-LEGACY-* binding exists but functionid is NULL or a different function';
    END IF;

    SET v_exists = 0;
    SELECT COUNT(*) INTO v_exists FROM `t_s_role_function`
        WHERE `ID` LIKE 'RF-TEMP-Q-%'
          AND (`functionid` IS NULL OR `functionid` <> 'FN-DAYCHECK-TEMPERATURE-QUERY');
    IF v_exists > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'seed aborted: an RF-TEMP-Q-* binding exists but functionid is NULL or a different function';
    END IF;

    -- (7) 资源行与绑定行的 INSERT 序列包在事务里，失败由 EXIT HANDLER 回滚。
    START TRANSACTION;

    -- (5) 纯增量插入资源行（存在即跳过，不覆盖既有字段）。
    INSERT INTO `t_s_function`
        (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`,
         `functionurl`, `parentfunctionid`, `functiontype`)
    SELECT 'FN-DAYCHECK-YICHANG-LEGACY', NULL, 2, '出货异常查询', '96',
           '/daycheck/yi-chang/get-yichang-down', NULL, 1
    WHERE NOT EXISTS (SELECT 1 FROM `t_s_function` WHERE `ID` = 'FN-DAYCHECK-YICHANG-LEGACY');

    INSERT INTO `t_s_function`
        (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`,
         `functionurl`, `parentfunctionid`, `functiontype`)
    SELECT 'FN-DAYCHECK-YICHANG-PAGE', NULL, 2, '出货异常查询（巡检分页）', '97',
           '/daycheck/yi-chang/get-yichang-down-page', NULL, 1
    WHERE NOT EXISTS (SELECT 1 FROM `t_s_function` WHERE `ID` = 'FN-DAYCHECK-YICHANG-PAGE');

    INSERT INTO `t_s_function`
        (`ID`, `functioniframe`, `functionlevel`, `functionname`, `functionorder`,
         `functionurl`, `parentfunctionid`, `functiontype`)
    SELECT 'FN-DAYCHECK-TEMPERATURE-QUERY', NULL, 2, '温度巡检查询', '98',
           '/daycheck/temperature/query', NULL, 1
    WHERE NOT EXISTS (SELECT 1 FROM `t_s_function` WHERE `ID` = 'FN-DAYCHECK-TEMPERATURE-QUERY');

    -- (5) 纯增量绑定：只新增缺失的绑定，保留既有其它角色不变。

    -- a) 出货异常新分页端点仅巡检使用：只绑 insp_read。
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-YC-PAGE-INSPECT', 'FN-DAYCHECK-YICHANG-PAGE', @insp_read_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'FN-DAYCHECK-YICHANG-PAGE' AND `roleid` = @insp_read_role_id);

    -- b) 出货异常旧端点（页面与巡检共用）：insp_read + 出货异常页面菜单的既有授权角色。
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-YC-LEGACY-INSPECT', 'FN-DAYCHECK-YICHANG-LEGACY', @insp_read_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'FN-DAYCHECK-YICHANG-LEGACY' AND `roleid` = @insp_read_role_id);

    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT DISTINCT CONCAT('RF-YC-LEGACY-', UPPER(r.`rolecode`)), 'FN-DAYCHECK-YICHANG-LEGACY', mr.`roleid`
    FROM `t_s_role_function` mr
    JOIN `t_s_role` r ON r.`ID` = mr.`roleid`
    WHERE mr.`functionid` = 'MENU-DAILY-CHECK-02'
      AND NOT EXISTS (
          SELECT 1 FROM `t_s_role_function` x
          WHERE x.`functionid` = 'FN-DAYCHECK-YICHANG-LEGACY' AND x.`roleid` = mr.`roleid`);

    -- c) 温度查询（页面与巡检共用）：insp_read + 温度维护页面菜单的既有授权角色。
    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT 'RF-TEMP-Q-INSPECT', 'FN-DAYCHECK-TEMPERATURE-QUERY', @insp_read_role_id
    WHERE NOT EXISTS (
        SELECT 1 FROM `t_s_role_function`
        WHERE `functionid` = 'FN-DAYCHECK-TEMPERATURE-QUERY' AND `roleid` = @insp_read_role_id);

    INSERT INTO `t_s_role_function` (`ID`, `functionid`, `roleid`)
    SELECT DISTINCT CONCAT('RF-TEMP-Q-', UPPER(r.`rolecode`)), 'FN-DAYCHECK-TEMPERATURE-QUERY', mr.`roleid`
    FROM `t_s_role_function` mr
    JOIN `t_s_role` r ON r.`ID` = mr.`roleid`
    WHERE mr.`functionid` = 'MENU-DAILY-CHECK-03'
      AND NOT EXISTS (
          SELECT 1 FROM `t_s_role_function` x
          WHERE x.`functionid` = 'FN-DAYCHECK-TEMPERATURE-QUERY' AND x.`roleid` = mr.`roleid`);

    COMMIT;
END//
DELIMITER ;

CALL `p_seed_daycheck_f016_inspection_role`();
DROP PROCEDURE `p_seed_daycheck_f016_inspection_role`;


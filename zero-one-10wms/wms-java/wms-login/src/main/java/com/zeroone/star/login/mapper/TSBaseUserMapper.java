package com.zeroone.star.login.mapper;


import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.zeroone.star.login.entity.TSBaseUser;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

import java.util.List;

/**
 * <p>
 * 系统用户 Mapper 接口
 * </p>
 *
 * @author nefertari
 * @since 2025-02-25
 */
@Mapper
public interface TSBaseUserMapper extends BaseMapper<TSBaseUser> {

    /** 按用户名查询角色编码。 */
    @Select(
            "SELECT r.rolecode " +
            "FROM t_s_role r " +
            "JOIN t_s_role_user ru ON r.ID = ru.roleid " +
            "JOIN t_s_base_user b ON b.ID = ru.userid " +
            "WHERE b.username = #{username}"
    )
    List<String> selectRoleCodesByUsername(String username);

    /** 按用户名查询基础用户（服务账号自签令牌需要 id / realname / 状态）。 */
    @Select(
            "SELECT ID, username, realname, status, delete_flag, departid "
            + "FROM t_s_base_user WHERE username = #{username}"
    )
    TSBaseUser selectBaseUserByUsername(String username);
}

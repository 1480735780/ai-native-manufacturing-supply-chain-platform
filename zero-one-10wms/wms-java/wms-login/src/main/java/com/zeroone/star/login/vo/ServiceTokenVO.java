package com.zeroone.star.login.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/** 服务账号令牌响应。 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ServiceTokenVO {

    /** 短时 JWT。 */
    private String token;

    /** 有效期（秒）。 */
    private Integer expiresIn;

    /** 服务账号用户名。 */
    private String userName;

    /** 服务账号角色。 */
    private List<String> roles;

    /** 服务账号允许访问的仓库范围。 */
    private List<String> warehouseScope;
}

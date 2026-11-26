package com.zeroone.star.project.security;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * 接口权限声明，用于代码审查、静态门禁与后续权限矩阵生成。
 *
 * <p>声明本身不会修改数据库、刷新网关缓存或自动放行接口。运行时仍以网关资源角色配置为准；
 * 新增接口必须同时完成资源登记/缓存刷新，删除、导出、财务和权限管理接口还必须经过人工评审。</p>
 *
 * <p>可标注在 Controller/API 接口类或处理方法上。类级声明是默认值，方法级声明覆盖类级声明。
 * {@code roles} 是“任一角色即可访问”的角色编码，不是 AND 关系，也不是数据范围；
 * 仓库/租户/本人范围仍须在业务层校验。{@code allowPublic=true} 只表示拟匿名访问，
 * 必须另行评审并显式加入网关 {@code white-paths}，不能仅凭注解绕过认证。</p>
 *
 * <p>{@code roles} 与 {@code allowPublic} 不能同时声明非空角色。方法上的 Spring Security
 * {@code @PreAuthorize} / {@code @Secured} / {@code @RolesAllowed} / {@code @PermitAll} /
 * {@code @DenyAll} 属于等价显式声明，静态检查器可识别，但必须确认运行时方法安全确实启用。</p>
 *
 * <pre>
 * &#64;RestController
 * &#64;RequestMapping("/daycheck")
 * &#64;ResourcePermission(roles = {"cg", "ckjl"})
 * public class DaycheckController {
 *
 *     &#64;GetMapping("/temperature/query")
 *     public JsonVO&lt;List&lt;TemperatureVO&gt;&gt; query() { ... }
 *
 *     &#64;PostMapping("/temperature/add")
 *     &#64;ResourcePermission(roles = {"ckjl"})
 *     public JsonVO&lt;String&gt; add() { ... }
 * }
 * </pre>
 *
 * @author zero-one
 * @since 1.0.0
 */
@Documented
@Retention(RetentionPolicy.RUNTIME)
@Target({ElementType.TYPE, ElementType.METHOD})
public @interface ResourcePermission {

    /** 允许访问的角色编码；多个角色为 OR 关系。默认空数组。 */
    String[] roles() default {};

    /** 是否拟匿名访问；默认 false。为 true 时不得同时配置 roles。 */
    boolean allowPublic() default false;
}

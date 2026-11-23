package io.github.bluemiaomiao.annotation;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * FastDFS 客户端启用标记。
 * 项目原私有 starter 已不可用，这里提供 Java 8 兼容的最小替代实现。
 */
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.TYPE)
public @interface EnableFastdfsClient {
}

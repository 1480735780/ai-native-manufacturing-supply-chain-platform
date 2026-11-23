package com.zeroone.star.project.components.fastdfs;

import io.github.bluemiaomiao.service.FastdfsClientService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * 注册 FastDFS 客户端（JDK 8 兼容实现）。
 */
@Configuration
public class FastdfsClientConfiguration {

    @Bean
    public FastdfsClientService fastdfsClientService(
            @Value("${fastdfs.tracker-servers:}") String trackerServers,
            @Value("${fastdfs.connect-timeout:5}") int connectTimeout,
            @Value("${fastdfs.network-timeout:30}") int networkTimeout,
            @Value("${fastdfs.charset:UTF-8}") String charset,
            @Value("${fastdfs.http-anti-steal-token:true}") boolean antiStealToken,
            @Value("${fastdfs.http-secret-key:}") String secretKey,
            @Value("${fastdfs.storage-ip:}") String storageIp,
            @Value("${fastdfs.storage-port:23000}") int storagePort) {
        return new FastdfsClientService(trackerServers, connectTimeout, networkTimeout,
                charset, antiStealToken, secretKey, storageIp, storagePort);
    }
}

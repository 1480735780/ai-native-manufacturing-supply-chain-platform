package io.github.bluemiaomiao.service;

import org.csource.fastdfs.ClientGlobal;
import org.csource.fastdfs.ProtoCommon;
import org.csource.fastdfs.StorageClient1;
import org.csource.fastdfs.StorageServer;
import org.csource.fastdfs.TrackerClient;
import org.csource.fastdfs.TrackerServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * FastDFS 客户端服务，基于 JDK 8 兼容的 fastdfs-client-java 实现。
 */
public class FastdfsClientService {

    private static final Logger log = LoggerFactory.getLogger(FastdfsClientService.class);

    private final String trackerServers;
    private final int connectTimeoutSeconds;
    private final int networkTimeoutSeconds;
    private final String charset;
    private final boolean antiStealToken;
    private final String secretKey;
    private final String storageIp;
    private final int storagePort;

    private volatile boolean initialized;

    public FastdfsClientService(String trackerServers, int connectTimeoutSeconds, int networkTimeoutSeconds,
                                String charset, boolean antiStealToken, String secretKey,
                                String storageIp, int storagePort) {
        this.trackerServers = trackerServers;
        this.connectTimeoutSeconds = connectTimeoutSeconds;
        this.networkTimeoutSeconds = networkTimeoutSeconds;
        this.charset = charset;
        this.antiStealToken = antiStealToken;
        this.secretKey = secretKey;
        this.storageIp = storageIp;
        this.storagePort = storagePort;
    }

    private void init() throws Exception {
        if (initialized) {
            return;
        }
        synchronized (this) {
            if (initialized) {
                return;
            }
            ClientGlobal.setG_connect_timeout(connectTimeoutSeconds * 1000);
            ClientGlobal.setG_network_timeout(networkTimeoutSeconds * 1000);
            ClientGlobal.setG_charset(charset);
            ClientGlobal.setG_anti_steal_token(antiStealToken);
            ClientGlobal.setG_secret_key(secretKey);
            ClientGlobal.initByTrackers(trackerServers);
            initialized = true;
            log.info("FastDFS 客户端初始化完成，tracker：{}", trackerServers);
        }
    }

    /**
     * 上传文件
     *
     * @param fileContent 文件内容
     * @param extName     扩展名，不含点
     * @return [0] 分组名，[1] 文件路径；失败返回 null
     */
    public String[] autoUpload(byte[] fileContent, String extName) throws Exception {
        init();
        String fileId;
        if (isStorageOverride()) {
            TrackerClient trackerClient = new TrackerClient();
            TrackerServer trackerServer = trackerClient.getTrackerServer();
            StorageServer storageServer = trackerClient.getStoreStorage(trackerServer, null);
            fileId = new StorageClient1(trackerServer, overrideStorage(storageServer))
                    .upload_file1(fileContent, extName, null);
        } else {
            fileId = new StorageClient1().upload_file1(fileContent, extName, null);
        }
        if (fileId == null) {
            log.error("FastDFS 上传失败，扩展名：{}", extName);
            return null;
        }
        int pos = fileId.indexOf('/');
        if (pos <= 0 || pos == fileId.length() - 1) {
            log.error("FastDFS 返回的文件ID格式不正确：{}", fileId);
            return null;
        }
        log.info("FastDFS 上传成功：{}", fileId);
        return new String[]{fileId.substring(0, pos), fileId.substring(pos + 1)};
    }

    /**
     * 下载文件
     */
    public byte[] download(String group, String storageId) throws Exception {
        init();
        if (!isStorageOverride()) {
            return new StorageClient1().download_file1(group + "/" + storageId);
        }
        TrackerClient trackerClient = new TrackerClient();
        TrackerServer trackerServer = trackerClient.getTrackerServer();
        StorageServer storageServer = trackerClient.getFetchStorage(trackerServer, group, storageId);
        return new StorageClient1(trackerServer, overrideStorage(storageServer))
                .download_file1(group + "/" + storageId);
    }

    /**
     * 删除文件
     *
     * @return 0 表示删除成功
     */
    public int delete(String group, String storageId) throws Exception {
        init();
        if (!isStorageOverride()) {
            return new StorageClient1().delete_file1(group + "/" + storageId);
        }
        TrackerClient trackerClient = new TrackerClient();
        TrackerServer trackerServer = trackerClient.getTrackerServer();
        StorageServer storageServer = trackerClient.getUpdateStorage(trackerServer, group, storageId);
        return new StorageClient1(trackerServer, overrideStorage(storageServer))
                .delete_file1(group + "/" + storageId);
    }

    /**
     * 生成带防盗链令牌的下载地址
     */
    public String autoDownloadWithToken(String group, String storageId, String urlPrefix) {
        try {
            init();
            int ts = (int) (System.currentTimeMillis() / 1000);
            String token = ProtoCommon.getToken(storageId, ts, secretKey);
            return buildUrl(urlPrefix, group, storageId) + "?token=" + token + "&ts=" + ts;
        } catch (Exception e) {
            log.error("生成带令牌下载地址失败：{}/{}", group, storageId, e);
            return null;
        }
    }

    /**
     * 生成不带令牌的下载地址
     */
    public String autoDownloadWithoutToken(String group, String storageId, String urlPrefix) {
        try {
            init();
            return buildUrl(urlPrefix, group, storageId);
        } catch (Exception e) {
            log.error("生成下载地址失败：{}/{}", group, storageId, e);
            return null;
        }
    }

    private boolean isStorageOverride() {
        return storageIp != null && !storageIp.trim().isEmpty();
    }

    private StorageServer overrideStorage(StorageServer storageServer) throws Exception {
        if (storageServer == null) {
            throw new IllegalStateException("FastDFS 未返回可用的存储节点");
        }
        return new StorageServer(storageIp.trim(), storagePort, storageServer.getStorePathIndex());
    }

    private String buildUrl(String urlPrefix, String group, String storageId) {
        String prefix = urlPrefix == null ? "" : urlPrefix.trim();
        if (prefix.endsWith("/")) {
            prefix = prefix.substring(0, prefix.length() - 1);
        }
        if (!prefix.startsWith("http://") && !prefix.startsWith("https://")) {
            prefix = "http://" + prefix;
        }
        return prefix + "/" + group + "/" + storageId;
    }
}

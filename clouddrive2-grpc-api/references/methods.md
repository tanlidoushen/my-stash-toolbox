# CloudDrive2 gRPC 完整方法清单（v1.0.13）

> 来源：官方 `https://www.clouddrive2.com/api/clouddrive.proto`（官网最新版），`service CloudDriveFileSrv` 共 **226 个活跃 RPC**（proto 中注释掉的 `APILoginPikPak` 不计）。
> 分类按官方《CloudDrive2 gRPC API 开发者指南》章节；公共方法以官方指南「公共方法(无需授权)」列表为准（8 个）。
> 标 `stream` 的为服务端流式方法（响应多条）。除公共方法外均需 `Authorization: Bearer <token>` 元数据头。

## 公共方法（无需授权，官方指南确认 8 个）（8）

| 方法 | 请求 | 响应 |
|---|---|---|
| `GetSystemInfo` | `google.protobuf.Empty` | `CloudDriveSystemInfo` |
| `GetToken` | `GetTokenRequest` | `JWTToken` |
| `Login` | `UserLoginRequest` | `FileOperationResult` |
| `LoginWithThirdPartyAccount` | `LoginWithThirdPartyAccountRequest` | `JWTToken` |
| `Register` | `UserRegisterRequest` | `FileOperationResult` |
| `SendResetAccountEmail` | `SendResetAccountEmailRequest` | `google.protobuf.Empty` |
| `ResetAccount` | `ResetAccountRequest` | `google.protobuf.Empty` |
| `GetApiTokenInfo` | `StringValue` | `TokenInfo` |

## 账号 / 2FA / 会话 / 设备（24）

| 方法 | 请求 | 响应 |
|---|---|---|
| `SendDisable2FAEmail` | `SendDisable2FAEmailRequest` | `google.protobuf.Empty` |
| `Disable2FAByEmail` | `Disable2FAByEmailRequest` | `google.protobuf.Empty` |
| `LoginWith2FA` | `LoginWith2FARequest` | `JWTToken` |
| `SendConfirmEmail` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `ConfirmEmail` | `ConfirmEmailRequest` | `google.protobuf.Empty` |
| `GetAccountStatus` | `google.protobuf.Empty` | `AccountStatusResult` |
| `Check2FAStatus` | `google.protobuf.Empty` | `TwoFactorAuthStatusResult` |
| `Setup2FA` | `Setup2FARequest` | `TwoFactorAuthSetupResult` |
| `Enable2FA` | `TwoFactorAuthCodeRequest` | `TwoFactorAuthEnableResult` |
| `Disable2FA` | `TwoFactorAuthCodeRequest` | `TwoFactorAuthMessageResult` |
| `GetRecoveryCodes` | `TwoFactorAuthCodeRequest` | `TwoFactorAuthRecoveryCodesResult` |
| `RegenerateRecoveryCodes` | `TwoFactorAuthCodeRequest` | `TwoFactorAuthRecoveryCodesResult` |
| `UnbindDevice` | `UnbindDeviceRequest` | `google.protobuf.Empty` |
| `GetSessions` | `google.protobuf.Empty` | `GetSessionsResponse` |
| `RevokeSession` | `RevokeSessionRequest` | `google.protobuf.Empty` |
| `RevokeOtherSessions` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `Logout` | `UserLogoutRequest` | `FileOperationResult` |
| `ChangePassword` | `ChangePasswordRequest` | `FileOperationResult` |
| `SendChangeEmailCode` | `SendChangeEmailCodeRequest` | `google.protobuf.Empty` |
| `ChangeEmail` | `ChangeEmailRequest` | `google.protobuf.Empty` |
| `ChangeEmailAndPassword` | `ChangeEmailAndPasswordRequest` | `google.protobuf.Empty` |
| `GetMachineId` | `google.protobuf.Empty` | `StringResult` |
| `GetOnlineDevices` | `google.protobuf.Empty` | `OnlineDevices` |
| `KickoutDevice` | `DeviceRequest` | `google.protobuf.Empty` |

## 文件操作（28）

| 方法 | 请求 | 响应 |
|---|---|---|
| `GetSubFiles` | `ListSubFileRequest` | `stream SubFilesReply` |
| `GetSearchResults` | `SearchRequest` | `stream SubFilesReply` |
| `FindFileByPath` | `FindFileByPathRequest` | `CloudDriveFile` |
| `CreateFolder` | `CreateFolderRequest` | `CreateFolderResult` |
| `CreateEncryptedFolder` | `CreateEncryptedFolderRequest` | `CreateFolderResult` |
| `UnlockEncryptedFile` | `UnlockEncryptedFileRequest` | `FileOperationResult` |
| `LockEncryptedFile` | `FileRequest` | `FileOperationResult` |
| `RenameFile` | `RenameFileRequest` | `FileOperationResult` |
| `RenameFiles` | `RenameFilesRequest` | `FileOperationResult` |
| `MoveFile` | `MoveFileRequest` | `FileOperationResult` |
| `CopyFile` | `CopyFileRequest` | `FileOperationResult` |
| `DeleteFile` | `FileRequest` | `FileOperationResult` |
| `DeleteFilePermanently` | `FileRequest` | `FileOperationResult` |
| `DeleteFiles` | `MultiFileRequest` | `FileOperationResult` |
| `DeleteFilesPermanently` | `MultiFileRequest` | `FileOperationResult` |
| `GetFileDetailProperties` | `FileRequest` | `FileDetailProperties` |
| `GetSpaceInfo` | `FileRequest` | `SpaceInfo` |
| `GetCloudMemberships` | `FileRequest` | `CloudMemberships` |
| `GetMetaData` | `FileRequest` | `FileMetaData` |
| `GetOriginalPath` | `FileRequest` | `StringResult` |
| `CreateFile` | `CreateFileRequest` | `CreateFileResult` |
| `CloseFile` | `CloseFileRequest` | `FileOperationResult` |
| `WriteToFileStream` | `stream WriteFileRequest` | `WriteFileResult` |
| `WriteToFile` | `WriteFileRequest` | `WriteFileResult` |
| `SyncFileChangesFromCloud` | `FileRequest` | `FileSystemChangeStatistics` |
| `StartCloudEventListener` | `FileRequest` | `google.protobuf.Empty` |
| `StopCloudEventListener` | `FileRequest` | `google.protobuf.Empty` |
| `WalkThroughFolderTest` | `FileRequest` | `WalkThroughFolderResult` |

## 缓存 / 预取 / 运行时（23）

| 方法 | 请求 | 响应 |
|---|---|---|
| `GetRuntimeInfo` | `google.protobuf.Empty` | `RuntimeInfo` |
| `GetFileBufferDiskCacheStats` | `google.protobuf.Empty` | `FileBufferDiskCacheStats` |
| `PurgeFileBufferDiskCache` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `SetDiskCacheEvictionStrategy` | `SetDiskCacheEvictionStrategyRequest` | `google.protobuf.Empty` |
| `SetFolderDiskCache` | `SetFolderDiskCacheRequest` | `google.protobuf.Empty` |
| `RemoveFolderDiskCache` | `FileRequest` | `google.protobuf.Empty` |
| `ListDiskCacheFolders` | `google.protobuf.Empty` | `ListDiskCacheFoldersReply` |
| `PrefetchFileRanges` | `PrefetchFileRangesRequest` | `PrefetchFileRangesReply` |
| `CancelFilePrefetch` | `CancelFilePrefetchRequest` | `google.protobuf.Empty` |
| `CloseFileReader` | `FileRequest` | `google.protobuf.Empty` |
| `GetActivePrefetchHints` | `google.protobuf.Empty` | `GetActivePrefetchHintsReply` |
| `GetRunningInfo` | `google.protobuf.Empty` | `RunInfo` |
| `GetOpenFileHandles` | `google.protobuf.Empty` | `OpenFileHandleList` |
| `SetDirCacheTimeSecs` | `SetDirCacheTimeRequest` | `google.protobuf.Empty` |
| `GetEffectiveDirCacheTimeSecs` | `GetEffectiveDirCacheTimeRequest` | `GetEffectiveDirCacheTimeResult` |
| `ForceExpireDirCache` | `FileRequest` | `google.protobuf.Empty` |
| `VacuumDirCache` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `GetVacuumProgress` | `google.protobuf.Empty` | `VacuumProgressResult` |
| `GetDirCacheDbSize` | `google.protobuf.Empty` | `GetDirCacheDbSizeResult` |
| `GetOpenFileTable` | `GetOpenFileTableRequest` | `OpenFileTable` |
| `GetDirCacheTable` | `google.protobuf.Empty` | `DirCacheTable` |
| `GetReferencedEntryPaths` | `FileRequest` | `StringList` |
| `GetTempFileTable` | `google.protobuf.Empty` | `TempFileTable` |

## 离线下载 / 分享（8）

| 方法 | 请求 | 响应 |
|---|---|---|
| `AddOfflineFiles` | `AddOfflineFileRequest` | `FileOperationResult` |
| `RemoveOfflineFiles` | `RemoveOfflineFilesRequest` | `FileOperationResult` |
| `ListOfflineFilesByPath` | `FileRequest` | `OfflineFileListResult` |
| `ListAllOfflineFiles` | `OfflineFileListAllRequest` | `OfflineFileListAllResult` |
| `GetOfflineQuotaInfo` | `OfflineQuotaRequest` | `OfflineQuotaInfo` |
| `ClearOfflineFiles` | `ClearOfflineFileRequest` | `google.protobuf.Empty` |
| `RestartOfflineTask` | `RestartOfflineFileRequest` | `google.protobuf.Empty` |
| `AddSharedLink` | `AddSharedLinkRequest` | `google.protobuf.Empty` |

## 挂载点管理（12）

| 方法 | 请求 | 响应 |
|---|---|---|
| `CanAddMoreMountPoints` | `google.protobuf.Empty` | `FileOperationResult` |
| `GetMountPoints` | `google.protobuf.Empty` | `GetMountPointsResult` |
| `AddMountPoint` | `MountOption` | `MountPointResult` |
| `RemoveMountPoint` | `MountPointRequest` | `MountPointResult` |
| `Mount` | `MountPointRequest` | `MountPointResult` |
| `Unmount` | `MountPointRequest` | `MountPointResult` |
| `UpdateMountPoint` | `UpdateMountPointRequest` | `MountPointResult` |
| `GetAvailableDriveLetters` | `google.protobuf.Empty` | `GetAvailableDriveLettersResult` |
| `HasDriveLetters` | `google.protobuf.Empty` | `HasDriveLettersResult` |
| `CanMountBothLocalAndCloud` | `google.protobuf.Empty` | `BoolResult` |
| `LocalGetSubFiles` | `LocalGetSubFilesRequest` | `stream LocalGetSubFilesResult` |
| `LocalCreateFolder` | `LocalCreateFolderRequest` | `LocalCreateFolderResult` |

## 传输任务（下载/上传/复制/合并）（24）

| 方法 | 请求 | 响应 |
|---|---|---|
| `GetAllTasksCount` | `google.protobuf.Empty` | `GetAllTasksCountResult` |
| `GetDownloadFileCount` | `google.protobuf.Empty` | `GetDownloadFileCountResult` |
| `GetDownloadFileList` | `google.protobuf.Empty` | `GetDownloadFileListResult` |
| `GetUploadFileCount` | `google.protobuf.Empty` | `GetUploadFileCountResult` |
| `GetUploadFileList` | `GetUploadFileListRequest` | `GetUploadFileListResult` |
| `CancelAllUploadFiles` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `CancelUploadFiles` | `MultpleUploadFileKeyRequest` | `google.protobuf.Empty` |
| `PauseAllUploadFiles` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `PauseUploadFiles` | `MultpleUploadFileKeyRequest` | `google.protobuf.Empty` |
| `ResumeAllUploadFiles` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `ResumeUploadFiles` | `MultpleUploadFileKeyRequest` | `google.protobuf.Empty` |
| `GetCopyTasks` | `google.protobuf.Empty` | `GetCopyTaskResult` |
| `GetMergeTasks` | `google.protobuf.Empty` | `GetMergeTasksResult` |
| `CancelMergeTask` | `CancelMergeTaskRequest` | `google.protobuf.Empty` |
| `CancelCopyTask` | `CopyTaskRequest` | `google.protobuf.Empty` |
| `PauseCopyTask` | `PauseCopyTaskRequest` | `google.protobuf.Empty` |
| `RestartCopyTask` | `CopyTaskRequest` | `google.protobuf.Empty` |
| `RemoveCompletedCopyTasks` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `RemoveAllCopyTasks` | `google.protobuf.Empty` | `BatchOperationResult` |
| `RemoveCopyTasks` | `CopyTaskBatchRequest` | `BatchOperationResult` |
| `PauseAllCopyTasks` | `PauseAllCopyTasksRequest` | `BatchOperationResult` |
| `PauseCopyTasks` | `PauseCopyTasksRequest` | `BatchOperationResult` |
| `ResumeAllCopyTasks` | `google.protobuf.Empty` | `BatchOperationResult` |
| `ResumeCopyTasks` | `CopyTaskBatchRequest` | `BatchOperationResult` |

## 云 API 管理（登录各云盘）（37）

| 方法 | 请求 | 响应 |
|---|---|---|
| `CanAddMoreCloudApis` | `google.protobuf.Empty` | `FileOperationResult` |
| `APILogin115Editthiscookie` | `Login115EditthiscookieRequest` | `APILoginResult` |
| `APILogin115QRCode` | `Login115QrCodeRequest` | `stream QRCodeScanMessage` |
| `APILogin115OpenOAuth` | `Login115OpenOAuthRequest` | `APILoginResult` |
| `APILogin115OpenQRCode` | `Login115OpenQRCodeRequest` | `stream QRCodeScanMessage` |
| `APILoginGuangYaPanQRCode` | `LoginGuangYaPanQRCodeRequest` | `stream QRCodeScanMessage` |
| `APILoginGuangYaPanOAuth` | `LoginGuangYaPanOAuthRequest` | `APILoginResult` |
| `APILoginAliyundriveOAuth` | `LoginAliyundriveOAuthRequest` | `APILoginResult` |
| `APILoginAliyundriveRefreshtoken` | `LoginAliyundriveRefreshtokenRequest` | `APILoginResult` |
| `APILoginAliyunDriveQRCode` | `LoginAliyundriveQRCodeRequest` | `stream QRCodeScanMessage` |
| `APILoginBaiduPanOAuth` | `LoginBaiduPanOAuthRequest` | `APILoginResult` |
| `APILoginOneDriveOAuth` | `LoginOneDriveOAuthRequest` | `APILoginResult` |
| `ApiLoginGoogleDriveOAuth` | `LoginGoogleDriveOAuthRequest` | `APILoginResult` |
| `ApiLoginGoogleDriveRefreshToken` | `LoginGoogleDriveRefreshTokenRequest` | `APILoginResult` |
| `ApiLoginXunleiOAuth` | `LoginXunleiOAuthRequest` | `APILoginResult` |
| `ApiLoginXunleiOpenOAuth` | `LoginXunleiOpenOAuthRequest` | `APILoginResult` |
| `ApiLogin123panOAuth` | `Login123panOAuthRequest` | `APILoginResult` |
| `CreateOAuthState` | `CreateOAuthStateRequest` | `CreateOAuthStateResult` |
| `APILogin189QRCode` | `Login189QRCodeRequest` | `stream QRCodeScanMessage` |
| `APILoginWebDav` | `LoginWebDavRequest` | `APILoginResult` |
| `APILoginS3` | `LoginS3Request` | `APILoginResult` |
| `APIAddLocalFolder` | `AddLocalFolderRequest` | `APILoginResult` |
| `APILoginCloudDrive` | `LoginCloudDriveRequest` | `APILoginResult` |
| `APILoginSftp` | `LoginSftpRequest` | `APILoginResult` |
| `APILoginFtp` | `LoginFtpRequest` | `APILoginResult` |
| `APILoginSmb` | `LoginSmbRequest` | `APILoginResult` |
| `DiscoverSmbServers` | `google.protobuf.Empty` | `DiscoverSmbServersResult` |
| `DiscoverSmbShares` | `DiscoverSmbSharesRequest` | `DiscoverSmbSharesResult` |
| `RemoveCloudAPI` | `RemoveCloudAPIRequest` | `FileOperationResult` |
| `GetAllCloudApis` | `google.protobuf.Empty` | `CloudAPIList` |
| `GetCloudAPIConfig` | `GetCloudAPIConfigRequest` | `CloudAPIConfig` |
| `SetCloudAPIConfig` | `SetCloudAPIConfigRequest` | `google.protobuf.Empty` |
| `GetPromotions` | `google.protobuf.Empty` | `GetPromotionsResult` |
| `GetPromotionsByCloud` | `CloudAPIRequest` | `GetPromotionsResult` |
| `UpdatePromotionResult` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `UpdatePromotionResultByCloud` | `UpdatePromotionResultByCloudRequest` | `google.protobuf.Empty` |
| `SendPromotionAction` | `SendPromotionActionRequest` | `google.protobuf.Empty` |

## 系统设置 / 服务 / 更新（15）

| 方法 | 请求 | 响应 |
|---|---|---|
| `GetSystemSettings` | `google.protobuf.Empty` | `SystemSettings` |
| `SetSystemSettings` | `SystemSettings` | `google.protobuf.Empty` |
| `GetCloudDrive1UserData` | `google.protobuf.Empty` | `StringResult` |
| `GetServiceCapabilities` | `google.protobuf.Empty` | `ServiceCapabilities` |
| `RestartService` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `ShutdownService` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `HasUpdate` | `google.protobuf.Empty` | `UpdateResult` |
| `CheckUpdate` | `google.protobuf.Empty` | `UpdateResult` |
| `DownloadUpdate` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `UpdateSystem` | `google.protobuf.Empty` | `google.protobuf.Empty` |
| `TestUpdate` | `FileRequest` | `google.protobuf.Empty` |
| `ListLogFiles` | `google.protobuf.Empty` | `ListLogFileResult` |
| `GetWebServerConfig` | `google.protobuf.Empty` | `WebServerConfig` |
| `SetWebServerConfig` | `SetWebServerConfigRequest` | `google.protobuf.Empty` |
| `GenerateSelfSignedCert` | `GenerateSelfSignedCertRequest` | `google.protobuf.Empty` |

## Webhook 配置（5）

| 方法 | 请求 | 响应 |
|---|---|---|
| `GetWebhookConfigTemplate` | `google.protobuf.Empty` | `StringResult` |
| `GetWebhookConfigs` | `google.protobuf.Empty` | `WebhookList` |
| `AddWebhookConfig` | `WebhookRequest` | `google.protobuf.Empty` |
| `RemoveWebhookConfig` | `StringValue` | `google.protobuf.Empty` |
| `ChangeWebhookConfig` | `WebhookRequest` | `google.protobuf.Empty` |

## WebDAV 管理（6）

| 方法 | 请求 | 响应 |
|---|---|---|
| `AddDavUser` | `AddDavUserRequest` | `google.protobuf.Empty` |
| `RemoveDavUser` | `StringValue` | `google.protobuf.Empty` |
| `ModifyDavUser` | `ModifyDavUserRequest` | `google.protobuf.Empty` |
| `GetDavUser` | `StringValue` | `DavUser` |
| `GetDavServerConfig` | `google.protobuf.Empty` | `DavServerConfig` |
| `SetDavServerConfig` | `ModifyDavServerConfigRequest` | `google.protobuf.Empty` |

## 令牌管理（4）

| 方法 | 请求 | 响应 |
|---|---|---|
| `CreateToken` | `CreateTokenRequest` | `TokenInfo` |
| `ModifyToken` | `ModifyTokenRequest` | `TokenInfo` |
| `RemoveToken` | `StringValue` | `google.protobuf.Empty` |
| `ListTokens` | `google.protobuf.Empty` | `ListTokensResult` |

## 远程上传协议（6）

| 方法 | 请求 | 响应 |
|---|---|---|
| `GetDownloadUrlPath` | `GetDownloadUrlPathRequest` | `DownloadUrlPathInfo` |
| `StartRemoteUpload` | `StartRemoteUploadRequest` | `RemoteUploadStarted` |
| `RemoteUploadControl` | `RemoteUploadControlRequest` | `google.protobuf.Empty` |
| `RemoteUploadChannel` | `RemoteUploadChannelRequest` | `stream RemoteUploadChannelReply` |
| `RemoteReadData` | `RemoteReadDataUpload` | `RemoteReadDataReply` |
| `RemoteHashProgress` | `RemoteHashProgressUpload` | `RemoteHashProgressReply` |

## 备份管理（13）

| 方法 | 请求 | 响应 |
|---|---|---|
| `BackupGetAll` | `google.protobuf.Empty` | `BackupList` |
| `BackupGetStatus` | `StringValue` | `BackupStatus` |
| `BackupAdd` | `Backup` | `google.protobuf.Empty` |
| `BackupRemove` | `StringValue` | `google.protobuf.Empty` |
| `BackupUpdate` | `Backup` | `google.protobuf.Empty` |
| `BackupAddDestination` | `BackupModifyRequest` | `google.protobuf.Empty` |
| `BackupRemoveDestination` | `BackupModifyRequest` | `google.protobuf.Empty` |
| `BackupSetEnabled` | `BackupSetEnabledRequest` | `google.protobuf.Empty` |
| `BackupSetFileSystemWatchEnabled` | `BackupModifyRequest` | `google.protobuf.Empty` |
| `BackupUpdateStrategies` | `BackupModifyRequest` | `google.protobuf.Empty` |
| `BackupRestartWalkingThrough` | `StringValue` | `google.protobuf.Empty` |
| `CanAddMoreBackups` | `google.protobuf.Empty` | `FileOperationResult` |
| `NotifyPhotoLibraryChanges` | `PhotoLibraryChangeList` | `google.protobuf.Empty` |

## 计划 / 会员 / 推广（11）

| 方法 | 请求 | 响应 |
|---|---|---|
| `GetCloudDrivePlans` | `google.protobuf.Empty` | `GetCloudDrivePlansResult` |
| `JoinPlan` | `JoinPlanRequest` | `JoinPlanResult` |
| `BindCloudAccount` | `BindCloudAccountRequest` | `google.protobuf.Empty` |
| `TransferBalance` | `TransferBalanceRequest` | `google.protobuf.Empty` |
| `GetBalanceLog` | `google.protobuf.Empty` | `BalanceLogResult` |
| `CheckActivationCode` | `StringValue` | `CheckActivationCodeResult` |
| `ActivatePlan` | `StringValue` | `JoinPlanResult` |
| `CheckCouponCode` | `CheckCouponCodeRequest` | `CouponCodeResult` |
| `GetStorePurchaseQuote` | `GetStorePurchaseQuoteRequest` | `StorePurchaseQuote` |
| `VerifyStorePurchase` | `VerifyStorePurchaseRequest` | `VerifyStorePurchaseResult` |
| `GetReferralCode` | `google.protobuf.Empty` | `StringValue` |

## 推送订阅（server-streaming）（2）

| 方法 | 请求 | 响应 |
|---|---|---|
| `PushTaskChange` | `google.protobuf.Empty` | `stream GetAllTasksCountResult` |
| `PushMessage` | `google.protobuf.Empty` | `stream CloudDrivePushMessage` |

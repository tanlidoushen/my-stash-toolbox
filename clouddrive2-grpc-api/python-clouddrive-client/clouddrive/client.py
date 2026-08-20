#!/usr/bin/env python3
# encoding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io>"
__all__ = ["Client", "CLOUDDRIVE_API_MAP"]

from collections.abc import Coroutine
from functools import cached_property
from typing import overload, Any, Iterable, Literal, Never, Sequence
from urllib.parse import urlsplit, urlunsplit

from google.protobuf.empty_pb2 import Empty # type: ignore
from google.protobuf.json_format import ParseDict # type: ignore
from google.protobuf.message import Message # type: ignore
from grpc import insecure_channel, Channel # type: ignore
from grpclib.client import Channel as AsyncChannel # type: ignore
from yarl import URL

import pathlib, sys
PROTO_DIR = str(pathlib.Path(__file__).parent / "proto")
if PROTO_DIR not in sys.path:
    sys.path.append(PROTO_DIR)

import clouddrive.pb2
from .proto import CloudDrive_grpc, CloudDrive_pb2_grpc


CLOUDDRIVE_API_MAP = {
    "GetSystemInfo": {"return": clouddrive.pb2.CloudDriveSystemInfo}, 
    "GetToken": {"argument": dict | clouddrive.pb2.GetTokenRequest, "return": clouddrive.pb2.JWTToken}, 
    "Login": {"argument": dict | clouddrive.pb2.UserLoginRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "LoginWithThirdPartyAccount": {"argument": dict | clouddrive.pb2.LoginWithThirdPartyAccountRequest, "return": clouddrive.pb2.JWTToken}, 
    "Register": {"argument": dict | clouddrive.pb2.UserRegisterRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "SendResetAccountEmail": {"argument": dict | clouddrive.pb2.SendResetAccountEmailRequest}, 
    "ResetAccount": {"argument": dict | clouddrive.pb2.ResetAccountRequest}, 
    "SendDisable2FAEmail": {"argument": dict | clouddrive.pb2.SendDisable2FAEmailRequest}, 
    "Disable2FAByEmail": {"argument": dict | clouddrive.pb2.Disable2FAByEmailRequest}, 
    "GetApiTokenInfo": {"argument": dict | clouddrive.pb2.StringValue, "return": clouddrive.pb2.TokenInfo}, 
    "LoginWith2FA": {"argument": dict | clouddrive.pb2.LoginWith2FARequest, "return": clouddrive.pb2.JWTToken}, 
    "SendConfirmEmail": {}, 
    "ConfirmEmail": {"argument": dict | clouddrive.pb2.ConfirmEmailRequest}, 
    "GetAccountStatus": {"return": clouddrive.pb2.AccountStatusResult}, 
    "Check2FAStatus": {"return": clouddrive.pb2.TwoFactorAuthStatusResult}, 
    "Setup2FA": {"argument": dict | clouddrive.pb2.Setup2FARequest, "return": clouddrive.pb2.TwoFactorAuthSetupResult}, 
    "Enable2FA": {"argument": dict | clouddrive.pb2.TwoFactorAuthCodeRequest, "return": clouddrive.pb2.TwoFactorAuthEnableResult}, 
    "Disable2FA": {"argument": dict | clouddrive.pb2.TwoFactorAuthCodeRequest, "return": clouddrive.pb2.TwoFactorAuthMessageResult}, 
    "GetRecoveryCodes": {"argument": dict | clouddrive.pb2.TwoFactorAuthCodeRequest, "return": clouddrive.pb2.TwoFactorAuthRecoveryCodesResult}, 
    "RegenerateRecoveryCodes": {"argument": dict | clouddrive.pb2.TwoFactorAuthCodeRequest, "return": clouddrive.pb2.TwoFactorAuthRecoveryCodesResult}, 
    "UnbindDevice": {"argument": dict | clouddrive.pb2.UnbindDeviceRequest}, 
    "GetSessions": {"return": clouddrive.pb2.GetSessionsResponse}, 
    "RevokeSession": {"argument": dict | clouddrive.pb2.RevokeSessionRequest}, 
    "RevokeOtherSessions": {}, 
    "GetSubFiles": {"argument": dict | clouddrive.pb2.ListSubFileRequest, "return": Iterable[clouddrive.pb2.SubFilesReply]}, 
    "GetSearchResults": {"argument": dict | clouddrive.pb2.SearchRequest, "return": Iterable[clouddrive.pb2.SubFilesReply]}, 
    "FindFileByPath": {"argument": dict | clouddrive.pb2.FindFileByPathRequest, "return": clouddrive.pb2.CloudDriveFile}, 
    "CreateFolder": {"argument": dict | clouddrive.pb2.CreateFolderRequest, "return": clouddrive.pb2.CreateFolderResult}, 
    "CreateEncryptedFolder": {"argument": dict | clouddrive.pb2.CreateEncryptedFolderRequest, "return": clouddrive.pb2.CreateFolderResult}, 
    "UnlockEncryptedFile": {"argument": dict | clouddrive.pb2.UnlockEncryptedFileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "LockEncryptedFile": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "RenameFile": {"argument": dict | clouddrive.pb2.RenameFileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "RenameFiles": {"argument": dict | clouddrive.pb2.RenameFilesRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "MoveFile": {"argument": dict | clouddrive.pb2.MoveFileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "CopyFile": {"argument": dict | clouddrive.pb2.CopyFileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "DeleteFile": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "DeleteFilePermanently": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "DeleteFiles": {"argument": dict | clouddrive.pb2.MultiFileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "DeleteFilesPermanently": {"argument": dict | clouddrive.pb2.MultiFileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "AddOfflineFiles": {"argument": dict | clouddrive.pb2.AddOfflineFileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "RemoveOfflineFiles": {"argument": dict | clouddrive.pb2.RemoveOfflineFilesRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "ListOfflineFilesByPath": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.OfflineFileListResult}, 
    "ListAllOfflineFiles": {"argument": dict | clouddrive.pb2.OfflineFileListAllRequest, "return": clouddrive.pb2.OfflineFileListAllResult}, 
    "GetOfflineQuotaInfo": {"argument": dict | clouddrive.pb2.OfflineQuotaRequest, "return": clouddrive.pb2.OfflineQuotaInfo}, 
    "ClearOfflineFiles": {"argument": dict | clouddrive.pb2.ClearOfflineFileRequest}, 
    "RestartOfflineTask": {"argument": dict | clouddrive.pb2.RestartOfflineFileRequest}, 
    "AddSharedLink": {"argument": dict | clouddrive.pb2.AddSharedLinkRequest}, 
    "GetFileDetailProperties": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.FileDetailProperties}, 
    "GetSpaceInfo": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.SpaceInfo}, 
    "GetCloudMemberships": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.CloudMemberships}, 
    "GetRuntimeInfo": {"return": clouddrive.pb2.RuntimeInfo}, 
    "GetFileBufferDiskCacheStats": {"return": clouddrive.pb2.FileBufferDiskCacheStats}, 
    "PurgeFileBufferDiskCache": {}, 
    "SetDiskCacheEvictionStrategy": {"argument": dict | clouddrive.pb2.SetDiskCacheEvictionStrategyRequest}, 
    "SetFolderDiskCache": {"argument": dict | clouddrive.pb2.SetFolderDiskCacheRequest}, 
    "RemoveFolderDiskCache": {"argument": dict | clouddrive.pb2.FileRequest}, 
    "ListDiskCacheFolders": {"return": clouddrive.pb2.ListDiskCacheFoldersReply}, 
    "PrefetchFileRanges": {"argument": dict | clouddrive.pb2.PrefetchFileRangesRequest, "return": clouddrive.pb2.PrefetchFileRangesReply}, 
    "CancelFilePrefetch": {"argument": dict | clouddrive.pb2.CancelFilePrefetchRequest}, 
    "CloseFileReader": {"argument": dict | clouddrive.pb2.FileRequest}, 
    "GetActivePrefetchHints": {"return": clouddrive.pb2.GetActivePrefetchHintsReply}, 
    "GetRunningInfo": {"return": clouddrive.pb2.RunInfo}, 
    "GetOpenFileHandles": {"return": clouddrive.pb2.OpenFileHandleList}, 
    "Logout": {"argument": dict | clouddrive.pb2.UserLogoutRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "CanAddMoreMountPoints": {"return": clouddrive.pb2.FileOperationResult}, 
    "GetMountPoints": {"return": clouddrive.pb2.GetMountPointsResult}, 
    "AddMountPoint": {"argument": dict | clouddrive.pb2.MountOption, "return": clouddrive.pb2.MountPointResult}, 
    "RemoveMountPoint": {"argument": dict | clouddrive.pb2.MountPointRequest, "return": clouddrive.pb2.MountPointResult}, 
    "Mount": {"argument": dict | clouddrive.pb2.MountPointRequest, "return": clouddrive.pb2.MountPointResult}, 
    "Unmount": {"argument": dict | clouddrive.pb2.MountPointRequest, "return": clouddrive.pb2.MountPointResult}, 
    "UpdateMountPoint": {"argument": dict | clouddrive.pb2.UpdateMountPointRequest, "return": clouddrive.pb2.MountPointResult}, 
    "GetAvailableDriveLetters": {"return": clouddrive.pb2.GetAvailableDriveLettersResult}, 
    "HasDriveLetters": {"return": clouddrive.pb2.HasDriveLettersResult}, 
    "CanMountBothLocalAndCloud": {"return": clouddrive.pb2.BoolResult}, 
    "LocalGetSubFiles": {"argument": dict | clouddrive.pb2.LocalGetSubFilesRequest, "return": Iterable[clouddrive.pb2.LocalGetSubFilesResult]}, 
    "LocalCreateFolder": {"argument": dict | clouddrive.pb2.LocalCreateFolderRequest, "return": clouddrive.pb2.LocalCreateFolderResult}, 
    "GetAllTasksCount": {"return": clouddrive.pb2.GetAllTasksCountResult}, 
    "GetDownloadFileCount": {"return": clouddrive.pb2.GetDownloadFileCountResult}, 
    "GetDownloadFileList": {"return": clouddrive.pb2.GetDownloadFileListResult}, 
    "GetUploadFileCount": {"return": clouddrive.pb2.GetUploadFileCountResult}, 
    "GetUploadFileList": {"argument": dict | clouddrive.pb2.GetUploadFileListRequest, "return": clouddrive.pb2.GetUploadFileListResult}, 
    "CancelAllUploadFiles": {}, 
    "CancelUploadFiles": {"argument": dict | clouddrive.pb2.MultpleUploadFileKeyRequest}, 
    "PauseAllUploadFiles": {}, 
    "PauseUploadFiles": {"argument": dict | clouddrive.pb2.MultpleUploadFileKeyRequest}, 
    "ResumeAllUploadFiles": {}, 
    "ResumeUploadFiles": {"argument": dict | clouddrive.pb2.MultpleUploadFileKeyRequest}, 
    "GetCopyTasks": {"return": clouddrive.pb2.GetCopyTaskResult}, 
    "GetMergeTasks": {"return": clouddrive.pb2.GetMergeTasksResult}, 
    "CancelMergeTask": {"argument": dict | clouddrive.pb2.CancelMergeTaskRequest}, 
    "CancelCopyTask": {"argument": dict | clouddrive.pb2.CopyTaskRequest}, 
    "PauseCopyTask": {"argument": dict | clouddrive.pb2.PauseCopyTaskRequest}, 
    "RestartCopyTask": {"argument": dict | clouddrive.pb2.CopyTaskRequest}, 
    "RemoveCompletedCopyTasks": {}, 
    "RemoveAllCopyTasks": {"return": clouddrive.pb2.BatchOperationResult}, 
    "RemoveCopyTasks": {"argument": dict | clouddrive.pb2.CopyTaskBatchRequest, "return": clouddrive.pb2.BatchOperationResult}, 
    "PauseAllCopyTasks": {"argument": dict | clouddrive.pb2.PauseAllCopyTasksRequest, "return": clouddrive.pb2.BatchOperationResult}, 
    "PauseCopyTasks": {"argument": dict | clouddrive.pb2.PauseCopyTasksRequest, "return": clouddrive.pb2.BatchOperationResult}, 
    "ResumeAllCopyTasks": {"return": clouddrive.pb2.BatchOperationResult}, 
    "ResumeCopyTasks": {"argument": dict | clouddrive.pb2.CopyTaskBatchRequest, "return": clouddrive.pb2.BatchOperationResult}, 
    "CanAddMoreCloudApis": {"return": clouddrive.pb2.FileOperationResult}, 
    "APILogin115Editthiscookie": {"argument": dict | clouddrive.pb2.Login115EditthiscookieRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILogin115QRCode": {"argument": dict | clouddrive.pb2.Login115QrCodeRequest, "return": Iterable[clouddrive.pb2.QRCodeScanMessage]}, 
    "APILogin115OpenOAuth": {"argument": dict | clouddrive.pb2.Login115OpenOAuthRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILogin115OpenQRCode": {"argument": dict | clouddrive.pb2.Login115OpenQRCodeRequest, "return": Iterable[clouddrive.pb2.QRCodeScanMessage]}, 
    "APILoginGuangYaPanQRCode": {"argument": dict | clouddrive.pb2.LoginGuangYaPanQRCodeRequest, "return": Iterable[clouddrive.pb2.QRCodeScanMessage]}, 
    "APILoginGuangYaPanOAuth": {"argument": dict | clouddrive.pb2.LoginGuangYaPanOAuthRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILoginAliyundriveOAuth": {"argument": dict | clouddrive.pb2.LoginAliyundriveOAuthRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILoginAliyundriveRefreshtoken": {"argument": dict | clouddrive.pb2.LoginAliyundriveRefreshtokenRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILoginAliyunDriveQRCode": {"argument": dict | clouddrive.pb2.LoginAliyundriveQRCodeRequest, "return": Iterable[clouddrive.pb2.QRCodeScanMessage]}, 
    "APILoginBaiduPanOAuth": {"argument": dict | clouddrive.pb2.LoginBaiduPanOAuthRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILoginOneDriveOAuth": {"argument": dict | clouddrive.pb2.LoginOneDriveOAuthRequest, "return": clouddrive.pb2.APILoginResult}, 
    "ApiLoginGoogleDriveOAuth": {"argument": dict | clouddrive.pb2.LoginGoogleDriveOAuthRequest, "return": clouddrive.pb2.APILoginResult}, 
    "ApiLoginGoogleDriveRefreshToken": {"argument": dict | clouddrive.pb2.LoginGoogleDriveRefreshTokenRequest, "return": clouddrive.pb2.APILoginResult}, 
    "ApiLoginXunleiOAuth": {"argument": dict | clouddrive.pb2.LoginXunleiOAuthRequest, "return": clouddrive.pb2.APILoginResult}, 
    "ApiLoginXunleiOpenOAuth": {"argument": dict | clouddrive.pb2.LoginXunleiOpenOAuthRequest, "return": clouddrive.pb2.APILoginResult}, 
    "ApiLogin123panOAuth": {"argument": dict | clouddrive.pb2.Login123panOAuthRequest, "return": clouddrive.pb2.APILoginResult}, 
    "CreateOAuthState": {"argument": dict | clouddrive.pb2.CreateOAuthStateRequest, "return": clouddrive.pb2.CreateOAuthStateResult}, 
    "APILogin189QRCode": {"argument": dict | clouddrive.pb2.Login189QRCodeRequest, "return": Iterable[clouddrive.pb2.QRCodeScanMessage]}, 
    "APILoginWebDav": {"argument": dict | clouddrive.pb2.LoginWebDavRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILoginS3": {"argument": dict | clouddrive.pb2.LoginS3Request, "return": clouddrive.pb2.APILoginResult}, 
    "APIAddLocalFolder": {"argument": dict | clouddrive.pb2.AddLocalFolderRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILoginCloudDrive": {"argument": dict | clouddrive.pb2.LoginCloudDriveRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILoginSftp": {"argument": dict | clouddrive.pb2.LoginSftpRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILoginFtp": {"argument": dict | clouddrive.pb2.LoginFtpRequest, "return": clouddrive.pb2.APILoginResult}, 
    "APILoginSmb": {"argument": dict | clouddrive.pb2.LoginSmbRequest, "return": clouddrive.pb2.APILoginResult}, 
    "DiscoverSmbServers": {"return": clouddrive.pb2.DiscoverSmbServersResult}, 
    "DiscoverSmbShares": {"argument": dict | clouddrive.pb2.DiscoverSmbSharesRequest, "return": clouddrive.pb2.DiscoverSmbSharesResult}, 
    "RemoveCloudAPI": {"argument": dict | clouddrive.pb2.RemoveCloudAPIRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "GetAllCloudApis": {"return": clouddrive.pb2.CloudAPIList}, 
    "GetCloudAPIConfig": {"argument": dict | clouddrive.pb2.GetCloudAPIConfigRequest, "return": clouddrive.pb2.CloudAPIConfig}, 
    "SetCloudAPIConfig": {"argument": dict | clouddrive.pb2.SetCloudAPIConfigRequest}, 
    "GetSystemSettings": {"return": clouddrive.pb2.SystemSettings}, 
    "SetSystemSettings": {"argument": dict | clouddrive.pb2.SystemSettings}, 
    "SetDirCacheTimeSecs": {"argument": dict | clouddrive.pb2.SetDirCacheTimeRequest}, 
    "GetEffectiveDirCacheTimeSecs": {"argument": dict | clouddrive.pb2.GetEffectiveDirCacheTimeRequest, "return": clouddrive.pb2.GetEffectiveDirCacheTimeResult}, 
    "ForceExpireDirCache": {"argument": dict | clouddrive.pb2.FileRequest}, 
    "VacuumDirCache": {}, 
    "GetVacuumProgress": {"return": clouddrive.pb2.VacuumProgressResult}, 
    "GetDirCacheDbSize": {"return": clouddrive.pb2.GetDirCacheDbSizeResult}, 
    "GetOpenFileTable": {"argument": dict | clouddrive.pb2.GetOpenFileTableRequest, "return": clouddrive.pb2.OpenFileTable}, 
    "GetDirCacheTable": {"return": clouddrive.pb2.DirCacheTable}, 
    "GetReferencedEntryPaths": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.StringList}, 
    "GetTempFileTable": {"return": clouddrive.pb2.TempFileTable}, 
    "PushTaskChange": {"return": Iterable[clouddrive.pb2.GetAllTasksCountResult]}, 
    "PushMessage": {"return": Iterable[clouddrive.pb2.CloudDrivePushMessage]}, 
    "GetCloudDrive1UserData": {"return": clouddrive.pb2.StringResult}, 
    "GetServiceCapabilities": {"return": clouddrive.pb2.ServiceCapabilities}, 
    "RestartService": {}, 
    "ShutdownService": {}, 
    "HasUpdate": {"return": clouddrive.pb2.UpdateResult}, 
    "CheckUpdate": {"return": clouddrive.pb2.UpdateResult}, 
    "DownloadUpdate": {}, 
    "UpdateSystem": {}, 
    "TestUpdate": {"argument": dict | clouddrive.pb2.FileRequest}, 
    "GetMetaData": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.FileMetaData}, 
    "GetOriginalPath": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.StringResult}, 
    "ChangePassword": {"argument": dict | clouddrive.pb2.ChangePasswordRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "CreateFile": {"argument": dict | clouddrive.pb2.CreateFileRequest, "return": clouddrive.pb2.CreateFileResult}, 
    "CloseFile": {"argument": dict | clouddrive.pb2.CloseFileRequest, "return": clouddrive.pb2.FileOperationResult}, 
    "WriteToFileStream": {"argument": Sequence[dict | clouddrive.pb2.WriteFileRequest], "return": clouddrive.pb2.WriteFileResult}, 
    "WriteToFile": {"argument": dict | clouddrive.pb2.WriteFileRequest, "return": clouddrive.pb2.WriteFileResult}, 
    "GetPromotions": {"return": clouddrive.pb2.GetPromotionsResult}, 
    "GetPromotionsByCloud": {"argument": dict | clouddrive.pb2.CloudAPIRequest, "return": clouddrive.pb2.GetPromotionsResult}, 
    "UpdatePromotionResult": {}, 
    "UpdatePromotionResultByCloud": {"argument": dict | clouddrive.pb2.UpdatePromotionResultByCloudRequest}, 
    "SendPromotionAction": {"argument": dict | clouddrive.pb2.SendPromotionActionRequest}, 
    "GetCloudDrivePlans": {"return": clouddrive.pb2.GetCloudDrivePlansResult}, 
    "JoinPlan": {"argument": dict | clouddrive.pb2.JoinPlanRequest, "return": clouddrive.pb2.JoinPlanResult}, 
    "BindCloudAccount": {"argument": dict | clouddrive.pb2.BindCloudAccountRequest}, 
    "TransferBalance": {"argument": dict | clouddrive.pb2.TransferBalanceRequest}, 
    "SendChangeEmailCode": {"argument": dict | clouddrive.pb2.SendChangeEmailCodeRequest}, 
    "ChangeEmail": {"argument": dict | clouddrive.pb2.ChangeEmailRequest}, 
    "ChangeEmailAndPassword": {"argument": dict | clouddrive.pb2.ChangeEmailAndPasswordRequest}, 
    "GetBalanceLog": {"return": clouddrive.pb2.BalanceLogResult}, 
    "CheckActivationCode": {"argument": dict | clouddrive.pb2.StringValue, "return": clouddrive.pb2.CheckActivationCodeResult}, 
    "ActivatePlan": {"argument": dict | clouddrive.pb2.StringValue, "return": clouddrive.pb2.JoinPlanResult}, 
    "CheckCouponCode": {"argument": dict | clouddrive.pb2.CheckCouponCodeRequest, "return": clouddrive.pb2.CouponCodeResult}, 
    "GetStorePurchaseQuote": {"argument": dict | clouddrive.pb2.GetStorePurchaseQuoteRequest, "return": clouddrive.pb2.StorePurchaseQuote}, 
    "VerifyStorePurchase": {"argument": dict | clouddrive.pb2.VerifyStorePurchaseRequest, "return": clouddrive.pb2.VerifyStorePurchaseResult}, 
    "GetReferralCode": {"return": clouddrive.pb2.StringValue}, 
    "BackupGetAll": {"return": clouddrive.pb2.BackupList}, 
    "BackupGetStatus": {"argument": dict | clouddrive.pb2.StringValue, "return": clouddrive.pb2.BackupStatus}, 
    "BackupAdd": {"argument": dict | clouddrive.pb2.Backup}, 
    "BackupRemove": {"argument": dict | clouddrive.pb2.StringValue}, 
    "BackupUpdate": {"argument": dict | clouddrive.pb2.Backup}, 
    "BackupAddDestination": {"argument": dict | clouddrive.pb2.BackupModifyRequest}, 
    "BackupRemoveDestination": {"argument": dict | clouddrive.pb2.BackupModifyRequest}, 
    "BackupSetEnabled": {"argument": dict | clouddrive.pb2.BackupSetEnabledRequest}, 
    "BackupSetFileSystemWatchEnabled": {"argument": dict | clouddrive.pb2.BackupModifyRequest}, 
    "BackupUpdateStrategies": {"argument": dict | clouddrive.pb2.BackupModifyRequest}, 
    "BackupRestartWalkingThrough": {"argument": dict | clouddrive.pb2.StringValue}, 
    "CanAddMoreBackups": {"return": clouddrive.pb2.FileOperationResult}, 
    "NotifyPhotoLibraryChanges": {"argument": dict | clouddrive.pb2.PhotoLibraryChangeList}, 
    "GetMachineId": {"return": clouddrive.pb2.StringResult}, 
    "GetOnlineDevices": {"return": clouddrive.pb2.OnlineDevices}, 
    "KickoutDevice": {"argument": dict | clouddrive.pb2.DeviceRequest}, 
    "ListLogFiles": {"return": clouddrive.pb2.ListLogFileResult}, 
    "SyncFileChangesFromCloud": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.FileSystemChangeStatistics}, 
    "StartCloudEventListener": {"argument": dict | clouddrive.pb2.FileRequest}, 
    "StopCloudEventListener": {"argument": dict | clouddrive.pb2.FileRequest}, 
    "WalkThroughFolderTest": {"argument": dict | clouddrive.pb2.FileRequest, "return": clouddrive.pb2.WalkThroughFolderResult}, 
    "GetWebhookConfigTemplate": {"return": clouddrive.pb2.StringResult}, 
    "GetWebhookConfigs": {"return": clouddrive.pb2.WebhookList}, 
    "AddWebhookConfig": {"argument": dict | clouddrive.pb2.WebhookRequest}, 
    "RemoveWebhookConfig": {"argument": dict | clouddrive.pb2.StringValue}, 
    "ChangeWebhookConfig": {"argument": dict | clouddrive.pb2.WebhookRequest}, 
    "AddDavUser": {"argument": dict | clouddrive.pb2.AddDavUserRequest}, 
    "RemoveDavUser": {"argument": dict | clouddrive.pb2.StringValue}, 
    "ModifyDavUser": {"argument": dict | clouddrive.pb2.ModifyDavUserRequest}, 
    "GetDavUser": {"argument": dict | clouddrive.pb2.StringValue, "return": clouddrive.pb2.DavUser}, 
    "GetDavServerConfig": {"return": clouddrive.pb2.DavServerConfig}, 
    "SetDavServerConfig": {"argument": dict | clouddrive.pb2.ModifyDavServerConfigRequest}, 
    "CreateToken": {"argument": dict | clouddrive.pb2.CreateTokenRequest, "return": clouddrive.pb2.TokenInfo}, 
    "ModifyToken": {"argument": dict | clouddrive.pb2.ModifyTokenRequest, "return": clouddrive.pb2.TokenInfo}, 
    "RemoveToken": {"argument": dict | clouddrive.pb2.StringValue}, 
    "ListTokens": {"return": clouddrive.pb2.ListTokensResult}, 
    "GetDownloadUrlPath": {"argument": dict | clouddrive.pb2.GetDownloadUrlPathRequest, "return": clouddrive.pb2.DownloadUrlPathInfo}, 
    "StartRemoteUpload": {"argument": dict | clouddrive.pb2.StartRemoteUploadRequest, "return": clouddrive.pb2.RemoteUploadStarted}, 
    "RemoteUploadControl": {"argument": dict | clouddrive.pb2.RemoteUploadControlRequest}, 
    "RemoteUploadChannel": {"argument": dict | clouddrive.pb2.RemoteUploadChannelRequest, "return": Iterable[clouddrive.pb2.RemoteUploadChannelReply]}, 
    "RemoteReadData": {"argument": dict | clouddrive.pb2.RemoteReadDataUpload, "return": clouddrive.pb2.RemoteReadDataReply}, 
    "RemoteHashProgress": {"argument": dict | clouddrive.pb2.RemoteHashProgressUpload, "return": clouddrive.pb2.RemoteHashProgressReply}, 
    "GetWebServerConfig": {"return": clouddrive.pb2.WebServerConfig}, 
    "SetWebServerConfig": {"argument": dict | clouddrive.pb2.SetWebServerConfigRequest}, 
    "GenerateSelfSignedCert": {"argument": dict | clouddrive.pb2.GenerateSelfSignedCertRequest}, 
}


def to_message(cls, o, /) -> Message:
    if isinstance(o, Message):
        return o
    elif type(o) is dict:
        return ParseDict(o, cls())
    elif type(o) is tuple:
        return cls(**{f.name: a for f, a in zip(cls.DESCRIPTOR.fields, o)})
    else:
        return cls(**{cls.DESCRIPTOR.fields[0].name: o})


class Client:
    "clouddrive client that encapsulates grpc APIs"
    origin: URL
    username: str
    password: str
    download_baseurl: str
    metadata: list[tuple[str, str]]

    def __init__(
        self, 
        /, 
        origin: str = "http://localhost:19798", 
        username: str = "", 
        password: str = "", 
    ):
        origin = origin.rstrip("/")
        urlp = urlsplit(origin)
        scheme = urlp.scheme or "http"
        netloc = urlp.netloc or "localhost:19798"
        self.__dict__.update(
            origin = URL(urlunsplit(urlp._replace(scheme=scheme, netloc=netloc))), 
            download_baseurl = f"{scheme}://{netloc}/static/{scheme}/{netloc}/False/", 
            username = username, 
            password = password, 
            metadata = [], 
        )
        if username:
            self.login()

    def __del__(self, /):
        self.close()

    def __eq__(self, other, /) -> bool:
        return type(self) is type(other) and self.origin == other.origin and self.username == other.username

    def __hash__(self, /) -> int:
        return hash((self.origin, self.username))

    def __repr__(self, /) -> str:
        cls = type(self)
        module = cls.__module__
        name = cls.__qualname__
        if module != "__main__":
            name = module + "." + name
        return f"{name}(origin={self.origin!r}, username={self.username!r}, password='******')"

    def __setattr__(self, attr, val, /) -> Never:
        raise TypeError("can't set attribute")

    @cached_property
    def channel(self, /) -> Channel:
        return insecure_channel(self.origin.authority)

    @cached_property
    def stub(self, /) -> clouddrive.proto.CloudDrive_pb2_grpc.CloudDriveFileSrvStub:
        return CloudDrive_pb2_grpc.CloudDriveFileSrvStub(self.channel)

    @cached_property
    def async_channel(self, /) -> AsyncChannel:
        origin = self.origin
        return AsyncChannel(origin.host, origin.port)

    @cached_property
    def async_stub(self, /) -> clouddrive.proto.CloudDrive_grpc.CloudDriveFileSrvStub:
        return CloudDrive_grpc.CloudDriveFileSrvStub(self.async_channel)

    def close(self, /):
        ns = self.__dict__
        if "channel" in ns:
            ns["channel"].close()
        if "async_channel" in ns:
            ns["async_channel"].close()

    def set_password(self, value: str, /):
        self.__dict__["password"] = value
        self.login()

    def login(
        self, 
        /, 
        username: str = "", 
        password: str = "", 
    ):
        if not username:
            username = self.username
        if not password:
            password = self.password
        response = self.stub.GetToken(clouddrive.pb2.GetTokenRequest(userName=username, password=password))
        self.metadata[:] = [("authorization", "Bearer " + response.token),]

    @overload
    def GetSystemInfo(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CloudDriveSystemInfo:
        ...
    @overload
    def GetSystemInfo(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CloudDriveSystemInfo]:
        ...
    def GetSystemInfo(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CloudDriveSystemInfo | Coroutine[Any, Any, clouddrive.pb2.CloudDriveSystemInfo]:
        """
        public methods, no authorization is required
        returns if clouddrive has logged in to cloudfs server and the user name

        ------------------- protobuf rpc definition --------------------

        // public methods, no authorization is required
        // returns if clouddrive has logged in to cloudfs server and the user name
        rpc GetSystemInfo(google.protobuf.Empty) returns (CloudDriveSystemInfo) {}

        ------------------- protobuf type definition -------------------

        message CloudDriveSystemInfo {
          bool IsLogin = 1;
          string UserName = 2;
          bool SystemReady = 3;
          optional string SystemMessage = 4;
          optional bool hasError = 5;
          // device power and storage profile, see DevicePowerType
          DevicePowerType devicePowerType = 6;
          // true when dir cache persistence and disk buffer are force-disabled
          // (by platform config or SLOW_STORAGE device type)
          optional bool diskCacheDisabled = 7;
        }
        // Device power type — describes power and storage characteristics.
        // Set by the host app via C interface, exposed via GetSystemInfo.
        enum DevicePowerType {
          // Desktop/server: constant power, fast storage — no restrictions (default)
          DESKTOP = 0;
          // TV set / set-top box: constant power, slow flash storage
          // → local caches disabled, web UI should hide cache-heavy features
          SLOW_STORAGE = 1;
          // Phone / tablet: battery-powered, fast storage
          // → web UI should offer power-saving options when on battery
          BATTERY = 2;
        }
        """
        if async_:
            return self.async_stub.GetSystemInfo(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetSystemInfo(Empty(), metadata=self.metadata)

    @overload
    def GetToken(
        self, 
        arg: dict | clouddrive.pb2.GetTokenRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.JWTToken:
        ...
    @overload
    def GetToken(
        self, 
        arg: dict | clouddrive.pb2.GetTokenRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.JWTToken]:
        ...
    def GetToken(
        self, 
        arg: dict | clouddrive.pb2.GetTokenRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.JWTToken | Coroutine[Any, Any, clouddrive.pb2.JWTToken]:
        """
        get bearer token by username and password

        ------------------- protobuf rpc definition --------------------

        // get bearer token by username and password
        rpc GetToken(GetTokenRequest) returns (JWTToken) {}

        ------------------- protobuf type definition -------------------

        message GetTokenRequest {
          string userName = 1;
          string password = 2;
          optional string totpCode = 3; // Optional TOTP code for 2FA-enabled accounts
        }
        message JWTToken {
          bool success = 1;
          string errorMessage = 2;
          string token = 3;
          google.protobuf.Timestamp expiration = 4;
        }
        """
        arg = to_message(clouddrive.pb2.GetTokenRequest, arg)
        if async_:
            return self.async_stub.GetToken(arg, metadata=self.metadata)
        else:
            return self.stub.GetToken(arg, metadata=self.metadata)

    @overload
    def Login(
        self, 
        arg: dict | clouddrive.pb2.UserLoginRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def Login(
        self, 
        arg: dict | clouddrive.pb2.UserLoginRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def Login(
        self, 
        arg: dict | clouddrive.pb2.UserLoginRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        login to cloudfs server

        ------------------- protobuf rpc definition --------------------

        // login to cloudfs server
        rpc Login(UserLoginRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        message UserLoginRequest {
          string userName = 1;
          string password = 2;
          bool synDataToCloud = 3;
          optional ProxyInfo cloudfsProxy = 4; // Optional proxy for reaching CloudFS account server
        }
        """
        arg = to_message(clouddrive.pb2.UserLoginRequest, arg)
        if async_:
            return self.async_stub.Login(arg, metadata=self.metadata)
        else:
            return self.stub.Login(arg, metadata=self.metadata)

    @overload
    def LoginWithThirdPartyAccount(
        self, 
        arg: dict | clouddrive.pb2.LoginWithThirdPartyAccountRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.JWTToken:
        ...
    @overload
    def LoginWithThirdPartyAccount(
        self, 
        arg: dict | clouddrive.pb2.LoginWithThirdPartyAccountRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.JWTToken]:
        ...
    def LoginWithThirdPartyAccount(
        self, 
        arg: dict | clouddrive.pb2.LoginWithThirdPartyAccountRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.JWTToken | Coroutine[Any, Any, clouddrive.pb2.JWTToken]:
        """
        login with third party account (e.g., Xunlei)

        ------------------- protobuf rpc definition --------------------

        // login with third party account (e.g., Xunlei)
        rpc LoginWithThirdPartyAccount(LoginWithThirdPartyAccountRequest) returns (JWTToken) {}

        ------------------- protobuf type definition -------------------

        message JWTToken {
          bool success = 1;
          string errorMessage = 2;
          string token = 3;
          google.protobuf.Timestamp expiration = 4;
        }
        message LoginWithThirdPartyAccountRequest {
          string cloudName = 1;
          string refreshToken = 2;
          string accessToken = 3;
          uint64 expiresIn = 4;
          bool synDataToCloud = 5;
          optional ProxyInfo cloudfsProxy = 6; // Optional proxy for reaching CloudFS account server
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginWithThirdPartyAccountRequest, arg)
        if async_:
            return self.async_stub.LoginWithThirdPartyAccount(arg, metadata=self.metadata)
        else:
            return self.stub.LoginWithThirdPartyAccount(arg, metadata=self.metadata)

    @overload
    def Register(
        self, 
        arg: dict | clouddrive.pb2.UserRegisterRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def Register(
        self, 
        arg: dict | clouddrive.pb2.UserRegisterRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def Register(
        self, 
        arg: dict | clouddrive.pb2.UserRegisterRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        register a new count

        ------------------- protobuf rpc definition --------------------

        // register a new count
        rpc Register(UserRegisterRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        message UserRegisterRequest {
          string userName = 1;
          string password = 2;
          optional ProxyInfo cloudfsProxy = 3; // Optional proxy for reaching CloudFS account server
        }
        """
        arg = to_message(clouddrive.pb2.UserRegisterRequest, arg)
        if async_:
            return self.async_stub.Register(arg, metadata=self.metadata)
        else:
            return self.stub.Register(arg, metadata=self.metadata)

    @overload
    def SendResetAccountEmail(
        self, 
        arg: dict | clouddrive.pb2.SendResetAccountEmailRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SendResetAccountEmail(
        self, 
        arg: dict | clouddrive.pb2.SendResetAccountEmailRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SendResetAccountEmail(
        self, 
        arg: dict | clouddrive.pb2.SendResetAccountEmailRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        asks cloudfs server to send reset account email with reset link

        ------------------- protobuf rpc definition --------------------

        // asks cloudfs server to send reset account email with reset link
        rpc SendResetAccountEmail(SendResetAccountEmailRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message SendResetAccountEmailRequest { string email = 1; }
        """
        if async_:
            async def request():
                await self.async_stub.SendResetAccountEmail(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SendResetAccountEmail(arg, metadata=self.metadata)
            return None

    @overload
    def ResetAccount(
        self, 
        arg: dict | clouddrive.pb2.ResetAccountRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ResetAccount(
        self, 
        arg: dict | clouddrive.pb2.ResetAccountRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ResetAccount(
        self, 
        arg: dict | clouddrive.pb2.ResetAccountRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        reset account's data, set new password, with received reset code from email

        ------------------- protobuf rpc definition --------------------

        // reset account's data, set new password, with received reset code from email
        rpc ResetAccount(ResetAccountRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message ResetAccountRequest {
          string resetCode = 1;
          string newPassword = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.ResetAccount(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ResetAccount(arg, metadata=self.metadata)
            return None

    @overload
    def SendDisable2FAEmail(
        self, 
        arg: dict | clouddrive.pb2.SendDisable2FAEmailRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SendDisable2FAEmail(
        self, 
        arg: dict | clouddrive.pb2.SendDisable2FAEmailRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SendDisable2FAEmail(
        self, 
        arg: dict | clouddrive.pb2.SendDisable2FAEmailRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        recovery flow (no authorization): ask cloudfs to email a disable-2FA code to the account

        ------------------- protobuf rpc definition --------------------

        // recovery flow (no authorization): ask cloudfs to email a disable-2FA code to the account
        rpc SendDisable2FAEmail(SendDisable2FAEmailRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        message SendDisable2FAEmailRequest {
          string email = 1;
          optional ProxyInfo cloudfsProxy = 2; // Optional proxy for reaching CloudFS account server
        }
        """
        if async_:
            async def request():
                await self.async_stub.SendDisable2FAEmail(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SendDisable2FAEmail(arg, metadata=self.metadata)
            return None

    @overload
    def Disable2FAByEmail(
        self, 
        arg: dict | clouddrive.pb2.Disable2FAByEmailRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def Disable2FAByEmail(
        self, 
        arg: dict | clouddrive.pb2.Disable2FAByEmailRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def Disable2FAByEmail(
        self, 
        arg: dict | clouddrive.pb2.Disable2FAByEmailRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        recovery flow (no authorization): disable 2FA using the emailed code + account password

        ------------------- protobuf rpc definition --------------------

        // recovery flow (no authorization): disable 2FA using the emailed code + account password
        rpc Disable2FAByEmail(Disable2FAByEmailRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message Disable2FAByEmailRequest {
          string disable_code = 1; // UUID code from the recovery email
          string password = 2;     // clear-text account password; MD5-hashed by the backend before send
          optional ProxyInfo cloudfsProxy = 3; // Optional proxy for reaching CloudFS account server
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        if async_:
            async def request():
                await self.async_stub.Disable2FAByEmail(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.Disable2FAByEmail(arg, metadata=self.metadata)
            return None

    @overload
    def GetApiTokenInfo(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.TokenInfo:
        ...
    @overload
    def GetApiTokenInfo(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.TokenInfo]:
        ...
    def GetApiTokenInfo(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.TokenInfo | Coroutine[Any, Any, clouddrive.pb2.TokenInfo]:
        """
        get user created API token info by token string

        ------------------- protobuf rpc definition --------------------

        // get user created API token info by token string
        rpc GetApiTokenInfo(StringValue) returns (TokenInfo) {}

        ------------------- protobuf type definition -------------------

        message StringValue { string value = 1; }
        message TokenInfo {
          string token = 1;
          string rootDir = 2;
          TokenPermissions permissions = 3;
          // seconds from now until expiration. If absent or 0, the token never expires.
          optional uint64 expires_in = 4;
          string friendly_name = 5;
          bool enableGrpcLog = 6; // if true, log gRPC access to api_token-YYYY-MM-DD.log (default: false for admin tokens, true for user tokens)
          bool enableStreamFileLog = 7; // if true, log stream file access to api_token-YYYY-MM-DD.log (default: false for admin tokens, true for user tokens)
        }
        // --- End Remote Upload Protocol Messages ---
        message TokenPermissions {
          // File Operations
          bool allow_list = 1; // GetSubFiles, FindFileByPath
          bool allow_search = 2; // GetSearchResults
          bool allow_list_local =
              3; // LocalGetSubFiles, GetAvailableDriveLetters, HasDriveLetters
          bool allow_create_folder = 4; // CreateFolder, CreateEncryptedFolder
          bool allow_create_file = 5; // CreateFile, WriteToFile, WriteToFileStream
          bool allow_write = 6; // File uploads and copy operations
          bool allow_read = 7; // File downloads
          bool allow_rename = 8; // RenameFile, RenameFiles
          bool allow_move = 9; // MoveFile
          bool allow_copy = 10; // CopyFile
          bool allow_delete = 11; // DeleteFile, DeleteFiles
          bool allow_delete_permanently =
              12; // DeleteFilePermanently, DeleteFilesPermanently

          // Encryption Operations
          bool allow_create_encrypt = 13; // CreateEncryptedFolder
          bool allow_unlock_encrypted = 14; // UnlockEncryptedFile
          bool allow_lock_encrypted = 15; // LockEncryptedFile

          // Cloud Operations
          bool allow_add_offline_download = 16; // AddOfflineFiles
          bool allow_list_offline_downloads =
              17; // ListOfflineFilesByPath, ListAllOfflineFiles, GetOfflineQuotaInfo
          bool allow_modify_offline_downloads =
              18; // RemoveOfflineFiles, ClearOfflineFiles, RestartOfflineTask
          bool allow_shared_links = 19; // AddSharedLink

          // System Information
          bool allow_view_properties = 20; // GetFileDetailProperties
          bool allow_get_space_info = 21; // GetSpaceInfo
          bool allow_view_runtime_info = 22; // GetRuntimeInfo, GetRunningInfo
          bool allow_push_message = 41; // Receive push messages (file system changes,
                                        // transfer task updates, etc.)

          // Membership Management
          bool allow_get_memberships = 23; // GetCloudMemberships
          bool allow_modify_memberships =
              24; // Future membership modification operations

          // Mount Management
          bool allow_get_mounts = 25; // GetMountPoints, CanAddMoreMountPoints
          bool allow_modify_mounts =
              26; // AddMountPoint, RemoveMountPoint, Mount, Unmount, UpdateMountPoint

          // Transfer Management
          bool allow_get_transfer_tasks =
              27; // GetAllTasksCount, GetDownloadFileCount, GetDownloadFileList,
                  // GetUploadFileCount, GetUploadFileList, GetCopyTasks, GetMergeTasks
          bool allow_modify_transfer_tasks =
              28; // Cancel/Pause/Resume upload/download/copy operations

          // Cloud API Management
          bool allow_get_cloud_apis =
              29; // GetAllCloudApis, GetCloudAPIConfig, CanAddMoreCloudApis
          bool allow_modify_cloud_apis = 30; // Add/Remove cloud APIs, SetCloudAPIConfig

          // System Settings
          bool allow_get_system_settings =
              31; // GetSystemSettings, GetEffectiveDirCacheTimeSecs, GetDirCacheDbSize, GetVacuumProgress
          bool allow_modify_system_settings =
              32; // SetSystemSettings, SetDirCacheTimeSecs, ForceExpireDirCache, VacuumDirCache

          // Backup Management
          bool allow_get_backups =
              33; // BackupGetAll, BackupGetStatus, CanAddMoreBackups
          bool allow_modify_backups =
              34; // BackupAdd, BackupRemove, BackupUpdate, BackupSetEnabled, etc.

          // DAV Management
          bool allow_get_dav_config = 35; // GetDavUser, GetDavServerConfig
          bool allow_modify_dav_config =
              36; // AddDavUser, RemoveDavUser, ModifyDavUser, SetDavServerConfig

          // Token Management (Admin only)
          bool allow_token_management =
              37; // CreateToken, ModifyToken, RemoveToken, ListTokens

          // Account Management
          bool allow_get_account_info =
              38; // GetAccountStatus, GetBalanceLog, GetReferralCode
          bool allow_modify_account =
              39; // ChangePassword, ChangeEmail, TransferBalance

          // Service Control
          bool allow_service_control = 40; // RestartService, ShutdownService
        }
        """
        arg = to_message(clouddrive.pb2.StringValue, arg)
        if async_:
            return self.async_stub.GetApiTokenInfo(arg, metadata=self.metadata)
        else:
            return self.stub.GetApiTokenInfo(arg, metadata=self.metadata)

    @overload
    def LoginWith2FA(
        self, 
        arg: dict | clouddrive.pb2.LoginWith2FARequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.JWTToken:
        ...
    @overload
    def LoginWith2FA(
        self, 
        arg: dict | clouddrive.pb2.LoginWith2FARequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.JWTToken]:
        ...
    def LoginWith2FA(
        self, 
        arg: dict | clouddrive.pb2.LoginWith2FARequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.JWTToken | Coroutine[Any, Any, clouddrive.pb2.JWTToken]:
        """
        login with 2FA code (public method, no authorization required)

        ------------------- protobuf rpc definition --------------------

        // login with 2FA code (public method, no authorization required)
        rpc LoginWith2FA(LoginWith2FARequest) returns (JWTToken) {}

        ------------------- protobuf type definition -------------------

        message JWTToken {
          bool success = 1;
          string errorMessage = 2;
          string token = 3;
          google.protobuf.Timestamp expiration = 4;
        }
        message LoginWith2FARequest {
          string userName = 1;
          string password = 2;
          string totp_code = 3; // 6-digit TOTP code or 8-character recovery code
          bool synDataToCloud = 4;
          optional ProxyInfo cloudfsProxy = 5; // Optional proxy for reaching CloudFS account server
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginWith2FARequest, arg)
        if async_:
            return self.async_stub.LoginWith2FA(arg, metadata=self.metadata)
        else:
            return self.stub.LoginWith2FA(arg, metadata=self.metadata)

    @overload
    def SendConfirmEmail(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SendConfirmEmail(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SendConfirmEmail(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        authorized methods, Authorization header with Bearer {token} is requirerd
        asks cloudfs server to send confirm email with confirm link

        ------------------- protobuf rpc definition --------------------

        // authorized methods, Authorization header with Bearer {token} is requirerd
        // asks cloudfs server to send confirm email with confirm link
        rpc SendConfirmEmail(google.protobuf.Empty) returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.SendConfirmEmail(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SendConfirmEmail(Empty(), metadata=self.metadata)
            return None

    @overload
    def ConfirmEmail(
        self, 
        arg: dict | clouddrive.pb2.ConfirmEmailRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ConfirmEmail(
        self, 
        arg: dict | clouddrive.pb2.ConfirmEmailRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ConfirmEmail(
        self, 
        arg: dict | clouddrive.pb2.ConfirmEmailRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        confirm email by confirm code

        ------------------- protobuf rpc definition --------------------

        // confirm email by confirm code
        rpc ConfirmEmail(ConfirmEmailRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message ConfirmEmailRequest { string confirmCode = 1; }
        """
        if async_:
            async def request():
                await self.async_stub.ConfirmEmail(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ConfirmEmail(arg, metadata=self.metadata)
            return None

    @overload
    def GetAccountStatus(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.AccountStatusResult:
        ...
    @overload
    def GetAccountStatus(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.AccountStatusResult]:
        ...
    def GetAccountStatus(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.AccountStatusResult | Coroutine[Any, Any, clouddrive.pb2.AccountStatusResult]:
        """
        get account status

        ------------------- protobuf rpc definition --------------------

        // get account status
        rpc GetAccountStatus(google.protobuf.Empty) returns (AccountStatusResult) {}

        ------------------- protobuf type definition -------------------

        message AccountPlan {
          string planName = 1;
          string description = 2;
          string fontAwesomeIcon = 3;
          string durationDescription = 4;
          google.protobuf.Timestamp endTime = 5;
          string planId = 6;  // server plan id (\"1\"=Lifetime VIP, \"4\"=Lifetime Lite, etc.); \"0\"/empty if none
        }
        message AccountRole {
          string roleName = 1;
          string description = 2;
          optional int32 value = 3;
        }
        message AccountStatusResult {
          string userName = 1;
          string emailConfirmed = 2;
          double accountBalance = 3;
          AccountPlan accountPlan = 4;
          repeated AccountRole accountRoles = 5;
          optional AccountPlan secondPlan = 6;
          optional string partnerReferralCode = 7;
          optional bool trustedDevice = 8; // if true, the device is trusted, no need to
          // provide password for changing email and password
          optional bool userNameIsDeviceId =
              9; // if true, the deviceId is used as userName, which can be changed to
          // a real user name later
          repeated BoundDevice boundDevices =
              10; // partner devices this account is bound to (empty if none); drives the unbind UI
          optional SubscriptionInfo subscription = 11; // present only for a store auto-renew subscription (Apple/Google/Meta); null for Alipay/one-time
        }
        message BoundDevice {
          string deviceId = 1;
          string manufacturerId = 2;
          string status = 3;       // ACTIVE / INACTIVE / DELETED
          string createTime = 4;   // naive UTC datetime string
          string partnerName = 5;  // human-readable partner name (empty if missing)
        }
        // Auto-renew store subscription details (see iap-server-handoff §6.2).
        message SubscriptionInfo {
          string store = 1;        // apple | google | meta — where to manage it
          string productId = 2;    // cd_core_monthly | cd_core_yearly
          bool autoRenew = 3;      // false after the user cancels (access stays until expiresAt)
          bool inGracePeriod = 4;
          string expiresAt = 5;    // next auto-charge date (auto_renew) or access-end (naive UTC string)
        }
        """
        if async_:
            return self.async_stub.GetAccountStatus(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetAccountStatus(Empty(), metadata=self.metadata)

    @overload
    def Check2FAStatus(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthStatusResult:
        ...
    @overload
    def Check2FAStatus(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthStatusResult]:
        ...
    def Check2FAStatus(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthStatusResult | Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthStatusResult]:
        """
        ==================== 2FA Methods (Authorized) ====================
        Check if 2FA is enabled for the current user

        ------------------- protobuf rpc definition --------------------

        // ==================== 2FA Methods (Authorized) ====================
        // Check if 2FA is enabled for the current user
        rpc Check2FAStatus(google.protobuf.Empty) returns (TwoFactorAuthStatusResult) {}

        ------------------- protobuf type definition -------------------

        message TwoFactorAuthStatusResult {
          bool two_factor_enabled = 1;
        }
        """
        if async_:
            return self.async_stub.Check2FAStatus(Empty(), metadata=self.metadata)
        else:
            return self.stub.Check2FAStatus(Empty(), metadata=self.metadata)

    @overload
    def Setup2FA(
        self, 
        arg: dict | clouddrive.pb2.Setup2FARequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthSetupResult:
        ...
    @overload
    def Setup2FA(
        self, 
        arg: dict | clouddrive.pb2.Setup2FARequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthSetupResult]:
        ...
    def Setup2FA(
        self, 
        arg: dict | clouddrive.pb2.Setup2FARequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthSetupResult | Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthSetupResult]:
        """
        Setup 2FA - Generate TOTP secret and QR code (requires password)

        ------------------- protobuf rpc definition --------------------

        // Setup 2FA - Generate TOTP secret and QR code (requires password)
        rpc Setup2FA(Setup2FARequest) returns (TwoFactorAuthSetupResult) {}

        ------------------- protobuf type definition -------------------

        message Setup2FARequest {
          string password = 1;
        }
        message TwoFactorAuthSetupResult {
          string secret = 1;
          string qr_code = 2; // Base64-encoded PNG image (data URL format)
          string manual_entry_key = 3;
        }
        """
        arg = to_message(clouddrive.pb2.Setup2FARequest, arg)
        if async_:
            return self.async_stub.Setup2FA(arg, metadata=self.metadata)
        else:
            return self.stub.Setup2FA(arg, metadata=self.metadata)

    @overload
    def Enable2FA(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthEnableResult:
        ...
    @overload
    def Enable2FA(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthEnableResult]:
        ...
    def Enable2FA(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthEnableResult | Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthEnableResult]:
        """
        Enable 2FA by verifying TOTP code - Returns recovery codes

        ------------------- protobuf rpc definition --------------------

        // Enable 2FA by verifying TOTP code - Returns recovery codes
        rpc Enable2FA(TwoFactorAuthCodeRequest) returns (TwoFactorAuthEnableResult) {}

        ------------------- protobuf type definition -------------------

        message TwoFactorAuthCodeRequest {
          string totp_code = 1; // 6-digit TOTP code or 8-character recovery code
        }
        message TwoFactorAuthEnableResult {
          repeated string recovery_codes = 1;
          string message = 2;
        }
        """
        arg = to_message(clouddrive.pb2.TwoFactorAuthCodeRequest, arg)
        if async_:
            return self.async_stub.Enable2FA(arg, metadata=self.metadata)
        else:
            return self.stub.Enable2FA(arg, metadata=self.metadata)

    @overload
    def Disable2FA(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthMessageResult:
        ...
    @overload
    def Disable2FA(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthMessageResult]:
        ...
    def Disable2FA(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthMessageResult | Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthMessageResult]:
        """
        Disable 2FA - Requires valid TOTP code

        ------------------- protobuf rpc definition --------------------

        // Disable 2FA - Requires valid TOTP code
        rpc Disable2FA(TwoFactorAuthCodeRequest) returns (TwoFactorAuthMessageResult) {}

        ------------------- protobuf type definition -------------------

        message TwoFactorAuthCodeRequest {
          string totp_code = 1; // 6-digit TOTP code or 8-character recovery code
        }
        message TwoFactorAuthMessageResult {
          string message = 1;
        }
        """
        arg = to_message(clouddrive.pb2.TwoFactorAuthCodeRequest, arg)
        if async_:
            return self.async_stub.Disable2FA(arg, metadata=self.metadata)
        else:
            return self.stub.Disable2FA(arg, metadata=self.metadata)

    @overload
    def GetRecoveryCodes(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthRecoveryCodesResult:
        ...
    @overload
    def GetRecoveryCodes(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthRecoveryCodesResult]:
        ...
    def GetRecoveryCodes(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthRecoveryCodesResult | Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthRecoveryCodesResult]:
        """
        View unused recovery codes - Requires valid TOTP code

        ------------------- protobuf rpc definition --------------------

        // View unused recovery codes - Requires valid TOTP code
        rpc GetRecoveryCodes(TwoFactorAuthCodeRequest) returns (TwoFactorAuthRecoveryCodesResult) {}

        ------------------- protobuf type definition -------------------

        message TwoFactorAuthCodeRequest {
          string totp_code = 1; // 6-digit TOTP code or 8-character recovery code
        }
        message TwoFactorAuthRecoveryCodesResult {
          repeated string recovery_codes = 1;
          uint32 total = 2;
          string message = 3;
        }
        """
        arg = to_message(clouddrive.pb2.TwoFactorAuthCodeRequest, arg)
        if async_:
            return self.async_stub.GetRecoveryCodes(arg, metadata=self.metadata)
        else:
            return self.stub.GetRecoveryCodes(arg, metadata=self.metadata)

    @overload
    def RegenerateRecoveryCodes(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthRecoveryCodesResult:
        ...
    @overload
    def RegenerateRecoveryCodes(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthRecoveryCodesResult]:
        ...
    def RegenerateRecoveryCodes(
        self, 
        arg: dict | clouddrive.pb2.TwoFactorAuthCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.TwoFactorAuthRecoveryCodesResult | Coroutine[Any, Any, clouddrive.pb2.TwoFactorAuthRecoveryCodesResult]:
        """
        Regenerate recovery codes - Requires valid TOTP code

        ------------------- protobuf rpc definition --------------------

        // Regenerate recovery codes - Requires valid TOTP code
        rpc RegenerateRecoveryCodes(TwoFactorAuthCodeRequest) returns (TwoFactorAuthRecoveryCodesResult) {}

        ------------------- protobuf type definition -------------------

        message TwoFactorAuthCodeRequest {
          string totp_code = 1; // 6-digit TOTP code or 8-character recovery code
        }
        message TwoFactorAuthRecoveryCodesResult {
          repeated string recovery_codes = 1;
          uint32 total = 2;
          string message = 3;
        }
        """
        arg = to_message(clouddrive.pb2.TwoFactorAuthCodeRequest, arg)
        if async_:
            return self.async_stub.RegenerateRecoveryCodes(arg, metadata=self.metadata)
        else:
            return self.stub.RegenerateRecoveryCodes(arg, metadata=self.metadata)

    @overload
    def UnbindDevice(
        self, 
        arg: dict | clouddrive.pb2.UnbindDeviceRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def UnbindDevice(
        self, 
        arg: dict | clouddrive.pb2.UnbindDeviceRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def UnbindDevice(
        self, 
        arg: dict | clouddrive.pb2.UnbindDeviceRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        Detach all devices bound to the account (lost/sold device). Requires password (+ TOTP if 2FA on)

        ------------------- protobuf rpc definition --------------------

        // Detach all devices bound to the account (lost/sold device). Requires password (+ TOTP if 2FA on)
        rpc UnbindDevice(UnbindDeviceRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message UnbindDeviceRequest {
          string password = 1;          // clear-text account password; MD5-hashed by the backend
          optional string totp_code = 2; // required only when 2FA is enabled
        }

        // ==================== End 2FA Messages ====================
        """
        if async_:
            async def request():
                await self.async_stub.UnbindDevice(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.UnbindDevice(arg, metadata=self.metadata)
            return None

    @overload
    def GetSessions(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetSessionsResponse:
        ...
    @overload
    def GetSessions(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetSessionsResponse]:
        ...
    def GetSessions(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetSessionsResponse | Coroutine[Any, Any, clouddrive.pb2.GetSessionsResponse]:
        """
        ==================== Session Management Methods ====================
        Get list of all active refresh token sessions

        ------------------- protobuf rpc definition --------------------

        // ==================== Session Management Methods ====================
        // Get list of all active refresh token sessions
        rpc GetSessions(google.protobuf.Empty) returns (GetSessionsResponse) {}

        ------------------- protobuf type definition -------------------

        message GetSessionsResponse {
          repeated Session sessions = 1;
        }
        // ==================== Session Management Messages ====================
        message Session {
          string id = 1;
          string device_id = 2;
          string device_name = 3;
          string device_os_type = 4;
          string created_at = 5;
          string last_used_at = 6;
          string expires_at = 7;
          string last_ip_address = 8;
        }
        """
        if async_:
            return self.async_stub.GetSessions(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetSessions(Empty(), metadata=self.metadata)

    @overload
    def RevokeSession(
        self, 
        arg: dict | clouddrive.pb2.RevokeSessionRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RevokeSession(
        self, 
        arg: dict | clouddrive.pb2.RevokeSessionRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RevokeSession(
        self, 
        arg: dict | clouddrive.pb2.RevokeSessionRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        Revoke a specific session by ID

        ------------------- protobuf rpc definition --------------------

        // Revoke a specific session by ID
        rpc RevokeSession(RevokeSessionRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message RevokeSessionRequest {
          string session_id = 1;
        }

        // ==================== End Session Management Messages ====================
        """
        if async_:
            async def request():
                await self.async_stub.RevokeSession(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RevokeSession(arg, metadata=self.metadata)
            return None

    @overload
    def RevokeOtherSessions(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RevokeOtherSessions(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RevokeOtherSessions(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        Revoke all sessions except the current one

        ------------------- protobuf rpc definition --------------------

        // Revoke all sessions except the current one
        rpc RevokeOtherSessions(google.protobuf.Empty) returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.RevokeOtherSessions(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RevokeOtherSessions(Empty(), metadata=self.metadata)
            return None

    @overload
    def GetSubFiles(
        self, 
        arg: dict | clouddrive.pb2.ListSubFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.SubFilesReply]:
        ...
    @overload
    def GetSubFiles(
        self, 
        arg: dict | clouddrive.pb2.ListSubFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.SubFilesReply]]:
        ...
    def GetSubFiles(
        self, 
        arg: dict | clouddrive.pb2.ListSubFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.SubFilesReply] | Coroutine[Any, Any, Iterable[clouddrive.pb2.SubFilesReply]]:
        """
        get all subfiles by path

        ------------------- protobuf rpc definition --------------------

        // get all subfiles by path
        rpc GetSubFiles(ListSubFileRequest) returns (stream SubFilesReply) {}

        ------------------- protobuf type definition -------------------

        message CloudDriveFile {
          string id = 1;
          string name = 2;
          string fullPathName = 3;
          int64 size = 4;
          enum FileType {
            Directory = 0;
            File = 1;
            Other = 2;
          }
          FileType fileType = 5;
          google.protobuf.Timestamp createTime = 6;
          google.protobuf.Timestamp writeTime = 7;
          google.protobuf.Timestamp accessTime = 8;
          CloudAPI CloudAPI = 9;
          string thumbnailUrl = 10;
          string previewUrl = 11;
          string originalPath = 14;

          bool isDirectory = 30;
          bool isRoot = 31;
          bool isCloudRoot = 32;
          bool isCloudDirectory = 33;
          bool isCloudFile = 34;
          bool isSearchResult = 35;
          bool isForbidden = 36;
          bool isLocal = 37;

          bool canMount = 60;
          bool canUnmount = 61;
          bool canDirectAccessThumbnailURL = 62;
          bool canSearch = 63;
          bool hasDetailProperties = 64;
          FileDetailProperties detailProperties = 65;
          bool canOfflineDownload = 66;
          bool canAddShareLink = 67;
          optional uint64 dirCacheTimeToLiveSecs = 68;
          bool canDeletePermanently = 69;
          // True when the owning cloud is read-only (GuangYaPan, etc.): all write ops
          // (create/rename/move/copy-into/delete/upload) are unsupported. Frontends hide
          // write actions on such items and disallow them as copy/move destinations.
          bool readOnly = 80;
          enum HashType {
            Unknown = 0;
            Md5 = 1;
            Sha1 = 2;
            PikPakSha1 = 3;
          }
          map<uint32, string> fileHashes = 70;
          enum FileEncryptionType {
            None = 0; // not encrypted
            Encrypted = 1; // encrypted, password not provided, a password is required
            // to unlock the file
            Unlocked = 2; // encrypted but but password is provided, can access the file
          }
          FileEncryptionType fileEncryptionType = 71;
          bool CanCreateEncryptedFolder = 72;
          bool CanLock = 73; // An unlocked encrypted file/folder can be locked
          bool CanSyncFileChangesFromCloud = 74; // File change can be synced from cloud
          bool supportOfflineDownloadManagement = 75; // can manage offline files
          bool canContentSearch = 79; // cloud supports content search (not just filename)

          // Download URL path with placeholders and expiration info for direct client
          // use Client replaces {SCHEME} with \"http\"/\"https\", {HOST} with actual
          // host:port, and {PREVIEW} with \"true\"/\"false\"
          optional DownloadUrlPathInfo downloadUrlPath = 76;
          // whether file buffer disk cache is enabled for this file/folder (resolved via ancestor)
          optional bool fileBufferDiskCacheEnabled = 77;
          // disk cache rules for this file/folder (resolved via ancestor, present only when enabled)
          optional DiskCacheFolder fileBufferDiskCacheRules = 78;
        }
        message ListSubFileRequest {
          string path = 1;
          bool forceRefresh = 2;
          optional bool checkExpires = 3;
        }
        message SubFilesReply { repeated CloudDriveFile subFiles = 1; }
        """
        arg = to_message(clouddrive.pb2.ListSubFileRequest, arg)
        if async_:
            return self.async_stub.GetSubFiles(arg, metadata=self.metadata)
        else:
            return self.stub.GetSubFiles(arg, metadata=self.metadata)

    @overload
    def GetSearchResults(
        self, 
        arg: dict | clouddrive.pb2.SearchRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.SubFilesReply]:
        ...
    @overload
    def GetSearchResults(
        self, 
        arg: dict | clouddrive.pb2.SearchRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.SubFilesReply]]:
        ...
    def GetSearchResults(
        self, 
        arg: dict | clouddrive.pb2.SearchRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.SubFilesReply] | Coroutine[Any, Any, Iterable[clouddrive.pb2.SubFilesReply]]:
        """
        search under path

        ------------------- protobuf rpc definition --------------------

        // search under path
        rpc GetSearchResults(SearchRequest) returns (stream SubFilesReply) {}

        ------------------- protobuf type definition -------------------

        message CloudDriveFile {
          string id = 1;
          string name = 2;
          string fullPathName = 3;
          int64 size = 4;
          enum FileType {
            Directory = 0;
            File = 1;
            Other = 2;
          }
          FileType fileType = 5;
          google.protobuf.Timestamp createTime = 6;
          google.protobuf.Timestamp writeTime = 7;
          google.protobuf.Timestamp accessTime = 8;
          CloudAPI CloudAPI = 9;
          string thumbnailUrl = 10;
          string previewUrl = 11;
          string originalPath = 14;

          bool isDirectory = 30;
          bool isRoot = 31;
          bool isCloudRoot = 32;
          bool isCloudDirectory = 33;
          bool isCloudFile = 34;
          bool isSearchResult = 35;
          bool isForbidden = 36;
          bool isLocal = 37;

          bool canMount = 60;
          bool canUnmount = 61;
          bool canDirectAccessThumbnailURL = 62;
          bool canSearch = 63;
          bool hasDetailProperties = 64;
          FileDetailProperties detailProperties = 65;
          bool canOfflineDownload = 66;
          bool canAddShareLink = 67;
          optional uint64 dirCacheTimeToLiveSecs = 68;
          bool canDeletePermanently = 69;
          // True when the owning cloud is read-only (GuangYaPan, etc.): all write ops
          // (create/rename/move/copy-into/delete/upload) are unsupported. Frontends hide
          // write actions on such items and disallow them as copy/move destinations.
          bool readOnly = 80;
          enum HashType {
            Unknown = 0;
            Md5 = 1;
            Sha1 = 2;
            PikPakSha1 = 3;
          }
          map<uint32, string> fileHashes = 70;
          enum FileEncryptionType {
            None = 0; // not encrypted
            Encrypted = 1; // encrypted, password not provided, a password is required
            // to unlock the file
            Unlocked = 2; // encrypted but but password is provided, can access the file
          }
          FileEncryptionType fileEncryptionType = 71;
          bool CanCreateEncryptedFolder = 72;
          bool CanLock = 73; // An unlocked encrypted file/folder can be locked
          bool CanSyncFileChangesFromCloud = 74; // File change can be synced from cloud
          bool supportOfflineDownloadManagement = 75; // can manage offline files
          bool canContentSearch = 79; // cloud supports content search (not just filename)

          // Download URL path with placeholders and expiration info for direct client
          // use Client replaces {SCHEME} with \"http\"/\"https\", {HOST} with actual
          // host:port, and {PREVIEW} with \"true\"/\"false\"
          optional DownloadUrlPathInfo downloadUrlPath = 76;
          // whether file buffer disk cache is enabled for this file/folder (resolved via ancestor)
          optional bool fileBufferDiskCacheEnabled = 77;
          // disk cache rules for this file/folder (resolved via ancestor, present only when enabled)
          optional DiskCacheFolder fileBufferDiskCacheRules = 78;
        }
        message SearchRequest {
          string path = 1;
          string searchFor = 2;
          bool forceRefresh = 3;
          bool fuzzyMatch = 4;
          optional bool addResultToMountedSearchFolder = 5; // if true, add search result to a mounted search folder
          optional bool contentSearch = 6; // if true, also search file content (not just filename), requires canContentSearch
        }
        message SubFilesReply { repeated CloudDriveFile subFiles = 1; }
        """
        arg = to_message(clouddrive.pb2.SearchRequest, arg)
        if async_:
            return self.async_stub.GetSearchResults(arg, metadata=self.metadata)
        else:
            return self.stub.GetSearchResults(arg, metadata=self.metadata)

    @overload
    def FindFileByPath(
        self, 
        arg: dict | clouddrive.pb2.FindFileByPathRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CloudDriveFile:
        ...
    @overload
    def FindFileByPath(
        self, 
        arg: dict | clouddrive.pb2.FindFileByPathRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CloudDriveFile]:
        ...
    def FindFileByPath(
        self, 
        arg: dict | clouddrive.pb2.FindFileByPathRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CloudDriveFile | Coroutine[Any, Any, clouddrive.pb2.CloudDriveFile]:
        """
        find file info by full path

        ------------------- protobuf rpc definition --------------------

        // find file info by full path
        rpc FindFileByPath(FindFileByPathRequest) returns (CloudDriveFile) {}

        ------------------- protobuf type definition -------------------

        message CloudAPI {
          string name = 1;
          string userName = 2;
          string nickName = 3;
          bool isLocked = 4; // isLocked means the cloudAPI is set to can't open files,
          // due to user's membership issue
          bool supportMultiThreadUploading = 5;
          bool supportQpsLimit = 6;
          bool isCloudEventListenerRunning = 7;
          bool hasPromotions = 8; // if true, this cloud has promotions
          optional string promotionTitle =
              9;                     // promotion title, if hasPromotions is true
          optional string path = 10; // the path of the cloud
          bool supportHttpDownload = 11; // whether this cloud provider supports HTTP (non-HTTPS) downloads
          bool readOnly = 12; // true when this cloud is read-only (all write ops unsupported)
        }
        message CloudDriveFile {
          string id = 1;
          string name = 2;
          string fullPathName = 3;
          int64 size = 4;
          enum FileType {
            Directory = 0;
            File = 1;
            Other = 2;
          }
          FileType fileType = 5;
          google.protobuf.Timestamp createTime = 6;
          google.protobuf.Timestamp writeTime = 7;
          google.protobuf.Timestamp accessTime = 8;
          CloudAPI CloudAPI = 9;
          string thumbnailUrl = 10;
          string previewUrl = 11;
          string originalPath = 14;

          bool isDirectory = 30;
          bool isRoot = 31;
          bool isCloudRoot = 32;
          bool isCloudDirectory = 33;
          bool isCloudFile = 34;
          bool isSearchResult = 35;
          bool isForbidden = 36;
          bool isLocal = 37;

          bool canMount = 60;
          bool canUnmount = 61;
          bool canDirectAccessThumbnailURL = 62;
          bool canSearch = 63;
          bool hasDetailProperties = 64;
          FileDetailProperties detailProperties = 65;
          bool canOfflineDownload = 66;
          bool canAddShareLink = 67;
          optional uint64 dirCacheTimeToLiveSecs = 68;
          bool canDeletePermanently = 69;
          // True when the owning cloud is read-only (GuangYaPan, etc.): all write ops
          // (create/rename/move/copy-into/delete/upload) are unsupported. Frontends hide
          // write actions on such items and disallow them as copy/move destinations.
          bool readOnly = 80;
          enum HashType {
            Unknown = 0;
            Md5 = 1;
            Sha1 = 2;
            PikPakSha1 = 3;
          }
          map<uint32, string> fileHashes = 70;
          enum FileEncryptionType {
            None = 0; // not encrypted
            Encrypted = 1; // encrypted, password not provided, a password is required
            // to unlock the file
            Unlocked = 2; // encrypted but but password is provided, can access the file
          }
          FileEncryptionType fileEncryptionType = 71;
          bool CanCreateEncryptedFolder = 72;
          bool CanLock = 73; // An unlocked encrypted file/folder can be locked
          bool CanSyncFileChangesFromCloud = 74; // File change can be synced from cloud
          bool supportOfflineDownloadManagement = 75; // can manage offline files
          bool canContentSearch = 79; // cloud supports content search (not just filename)

          // Download URL path with placeholders and expiration info for direct client
          // use Client replaces {SCHEME} with \"http\"/\"https\", {HOST} with actual
          // host:port, and {PREVIEW} with \"true\"/\"false\"
          optional DownloadUrlPathInfo downloadUrlPath = 76;
          // whether file buffer disk cache is enabled for this file/folder (resolved via ancestor)
          optional bool fileBufferDiskCacheEnabled = 77;
          // disk cache rules for this file/folder (resolved via ancestor, present only when enabled)
          optional DiskCacheFolder fileBufferDiskCacheRules = 78;
        }
        // A folder with disk cache rules
        message DiskCacheFolder {
          string path = 1;
          uint64 maxFileSize = 2;
          uint64 minFileSize = 3;
          ExtensionFilterMode extensionFilterMode = 4;
          repeated string extensions = 5;
          bool enabled = 6;
        }
        message DownloadUrlPathInfo {
          string downloadUrlPath = 1; // path and query part of the download URL with placeholders (e.g.,
                                      // \"/static/{SCHEME}/{HOST}/{PREVIEW}/path/to/file.txt?token=abc123\")
          optional uint64 expiresIn = 2; // seconds until expiration, none means never expire
          optional string directUrl = 3; // direct URL for download, if available, this will override downloadUrlPath
          optional string userAgent = 4; // user agent to be used when accessing directUrl
          map<string, string> additionalHeaders = 5; // additional headers to be used when accessing directUrl
        }
        message FileDetailProperties {
          int64 totalFileCount = 1;
          int64 totalFolderCount = 2;
          int64 totalSize = 3;
          bool isFaved = 4;
          bool isShared = 5;
          string originalPath = 6;
        }
        message FindFileByPathRequest {
          string parentPath = 1;
          string path = 2;
        }
        """
        arg = to_message(clouddrive.pb2.FindFileByPathRequest, arg)
        if async_:
            return self.async_stub.FindFileByPath(arg, metadata=self.metadata)
        else:
            return self.stub.FindFileByPath(arg, metadata=self.metadata)

    @overload
    def CreateFolder(
        self, 
        arg: dict | clouddrive.pb2.CreateFolderRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CreateFolderResult:
        ...
    @overload
    def CreateFolder(
        self, 
        arg: dict | clouddrive.pb2.CreateFolderRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CreateFolderResult]:
        ...
    def CreateFolder(
        self, 
        arg: dict | clouddrive.pb2.CreateFolderRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CreateFolderResult | Coroutine[Any, Any, clouddrive.pb2.CreateFolderResult]:
        """
        create a folder under path

        ------------------- protobuf rpc definition --------------------

        // create a folder under path
        rpc CreateFolder(CreateFolderRequest) returns (CreateFolderResult) {}

        ------------------- protobuf type definition -------------------

        message CloudDriveFile {
          string id = 1;
          string name = 2;
          string fullPathName = 3;
          int64 size = 4;
          enum FileType {
            Directory = 0;
            File = 1;
            Other = 2;
          }
          FileType fileType = 5;
          google.protobuf.Timestamp createTime = 6;
          google.protobuf.Timestamp writeTime = 7;
          google.protobuf.Timestamp accessTime = 8;
          CloudAPI CloudAPI = 9;
          string thumbnailUrl = 10;
          string previewUrl = 11;
          string originalPath = 14;

          bool isDirectory = 30;
          bool isRoot = 31;
          bool isCloudRoot = 32;
          bool isCloudDirectory = 33;
          bool isCloudFile = 34;
          bool isSearchResult = 35;
          bool isForbidden = 36;
          bool isLocal = 37;

          bool canMount = 60;
          bool canUnmount = 61;
          bool canDirectAccessThumbnailURL = 62;
          bool canSearch = 63;
          bool hasDetailProperties = 64;
          FileDetailProperties detailProperties = 65;
          bool canOfflineDownload = 66;
          bool canAddShareLink = 67;
          optional uint64 dirCacheTimeToLiveSecs = 68;
          bool canDeletePermanently = 69;
          // True when the owning cloud is read-only (GuangYaPan, etc.): all write ops
          // (create/rename/move/copy-into/delete/upload) are unsupported. Frontends hide
          // write actions on such items and disallow them as copy/move destinations.
          bool readOnly = 80;
          enum HashType {
            Unknown = 0;
            Md5 = 1;
            Sha1 = 2;
            PikPakSha1 = 3;
          }
          map<uint32, string> fileHashes = 70;
          enum FileEncryptionType {
            None = 0; // not encrypted
            Encrypted = 1; // encrypted, password not provided, a password is required
            // to unlock the file
            Unlocked = 2; // encrypted but but password is provided, can access the file
          }
          FileEncryptionType fileEncryptionType = 71;
          bool CanCreateEncryptedFolder = 72;
          bool CanLock = 73; // An unlocked encrypted file/folder can be locked
          bool CanSyncFileChangesFromCloud = 74; // File change can be synced from cloud
          bool supportOfflineDownloadManagement = 75; // can manage offline files
          bool canContentSearch = 79; // cloud supports content search (not just filename)

          // Download URL path with placeholders and expiration info for direct client
          // use Client replaces {SCHEME} with \"http\"/\"https\", {HOST} with actual
          // host:port, and {PREVIEW} with \"true\"/\"false\"
          optional DownloadUrlPathInfo downloadUrlPath = 76;
          // whether file buffer disk cache is enabled for this file/folder (resolved via ancestor)
          optional bool fileBufferDiskCacheEnabled = 77;
          // disk cache rules for this file/folder (resolved via ancestor, present only when enabled)
          optional DiskCacheFolder fileBufferDiskCacheRules = 78;
        }
        message CreateFolderRequest {
          string parentPath = 1;
          string folderName = 2;
        }
        message CreateFolderResult {
          CloudDriveFile folderCreated = 1;
          FileOperationResult result = 2;
        }
        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        """
        arg = to_message(clouddrive.pb2.CreateFolderRequest, arg)
        if async_:
            return self.async_stub.CreateFolder(arg, metadata=self.metadata)
        else:
            return self.stub.CreateFolder(arg, metadata=self.metadata)

    @overload
    def CreateEncryptedFolder(
        self, 
        arg: dict | clouddrive.pb2.CreateEncryptedFolderRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CreateFolderResult:
        ...
    @overload
    def CreateEncryptedFolder(
        self, 
        arg: dict | clouddrive.pb2.CreateEncryptedFolderRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CreateFolderResult]:
        ...
    def CreateEncryptedFolder(
        self, 
        arg: dict | clouddrive.pb2.CreateEncryptedFolderRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CreateFolderResult | Coroutine[Any, Any, clouddrive.pb2.CreateFolderResult]:
        """
        create an encrypted folder under path

        ------------------- protobuf rpc definition --------------------

        // create an encrypted folder under path
        rpc CreateEncryptedFolder(CreateEncryptedFolderRequest)
            returns (CreateFolderResult) {}

        ------------------- protobuf type definition -------------------

        message CloudDriveFile {
          string id = 1;
          string name = 2;
          string fullPathName = 3;
          int64 size = 4;
          enum FileType {
            Directory = 0;
            File = 1;
            Other = 2;
          }
          FileType fileType = 5;
          google.protobuf.Timestamp createTime = 6;
          google.protobuf.Timestamp writeTime = 7;
          google.protobuf.Timestamp accessTime = 8;
          CloudAPI CloudAPI = 9;
          string thumbnailUrl = 10;
          string previewUrl = 11;
          string originalPath = 14;

          bool isDirectory = 30;
          bool isRoot = 31;
          bool isCloudRoot = 32;
          bool isCloudDirectory = 33;
          bool isCloudFile = 34;
          bool isSearchResult = 35;
          bool isForbidden = 36;
          bool isLocal = 37;

          bool canMount = 60;
          bool canUnmount = 61;
          bool canDirectAccessThumbnailURL = 62;
          bool canSearch = 63;
          bool hasDetailProperties = 64;
          FileDetailProperties detailProperties = 65;
          bool canOfflineDownload = 66;
          bool canAddShareLink = 67;
          optional uint64 dirCacheTimeToLiveSecs = 68;
          bool canDeletePermanently = 69;
          // True when the owning cloud is read-only (GuangYaPan, etc.): all write ops
          // (create/rename/move/copy-into/delete/upload) are unsupported. Frontends hide
          // write actions on such items and disallow them as copy/move destinations.
          bool readOnly = 80;
          enum HashType {
            Unknown = 0;
            Md5 = 1;
            Sha1 = 2;
            PikPakSha1 = 3;
          }
          map<uint32, string> fileHashes = 70;
          enum FileEncryptionType {
            None = 0; // not encrypted
            Encrypted = 1; // encrypted, password not provided, a password is required
            // to unlock the file
            Unlocked = 2; // encrypted but but password is provided, can access the file
          }
          FileEncryptionType fileEncryptionType = 71;
          bool CanCreateEncryptedFolder = 72;
          bool CanLock = 73; // An unlocked encrypted file/folder can be locked
          bool CanSyncFileChangesFromCloud = 74; // File change can be synced from cloud
          bool supportOfflineDownloadManagement = 75; // can manage offline files
          bool canContentSearch = 79; // cloud supports content search (not just filename)

          // Download URL path with placeholders and expiration info for direct client
          // use Client replaces {SCHEME} with \"http\"/\"https\", {HOST} with actual
          // host:port, and {PREVIEW} with \"true\"/\"false\"
          optional DownloadUrlPathInfo downloadUrlPath = 76;
          // whether file buffer disk cache is enabled for this file/folder (resolved via ancestor)
          optional bool fileBufferDiskCacheEnabled = 77;
          // disk cache rules for this file/folder (resolved via ancestor, present only when enabled)
          optional DiskCacheFolder fileBufferDiskCacheRules = 78;
        }
        message CreateEncryptedFolderRequest {
          string parentPath = 1;
          string folderName = 2;
          string password = 3;
          bool savePassword = 4; // if true, password will be saved to db, else unlock
          // is required after restart
        }
        message CreateFolderResult {
          CloudDriveFile folderCreated = 1;
          FileOperationResult result = 2;
        }
        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        """
        arg = to_message(clouddrive.pb2.CreateEncryptedFolderRequest, arg)
        if async_:
            return self.async_stub.CreateEncryptedFolder(arg, metadata=self.metadata)
        else:
            return self.stub.CreateEncryptedFolder(arg, metadata=self.metadata)

    @overload
    def UnlockEncryptedFile(
        self, 
        arg: dict | clouddrive.pb2.UnlockEncryptedFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def UnlockEncryptedFile(
        self, 
        arg: dict | clouddrive.pb2.UnlockEncryptedFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def UnlockEncryptedFile(
        self, 
        arg: dict | clouddrive.pb2.UnlockEncryptedFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        unlock an encrypted folder/file by setting password

        ------------------- protobuf rpc definition --------------------

        // unlock an encrypted folder/file by setting password
        rpc UnlockEncryptedFile(UnlockEncryptedFileRequest)
            returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message UnlockEncryptedFileRequest {
          string path = 1;
          string password = 2;
          bool permanentUnlock = 3; // if true, password will be saved to db, else
          // unlock is required after restart
        }
        """
        arg = to_message(clouddrive.pb2.UnlockEncryptedFileRequest, arg)
        if async_:
            return self.async_stub.UnlockEncryptedFile(arg, metadata=self.metadata)
        else:
            return self.stub.UnlockEncryptedFile(arg, metadata=self.metadata)

    @overload
    def LockEncryptedFile(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def LockEncryptedFile(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def LockEncryptedFile(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        lock an encrypted folder/file by clearing password

        ------------------- protobuf rpc definition --------------------

        // lock an encrypted folder/file by clearing password
        rpc LockEncryptedFile(FileRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.LockEncryptedFile(arg, metadata=self.metadata)
        else:
            return self.stub.LockEncryptedFile(arg, metadata=self.metadata)

    @overload
    def RenameFile(
        self, 
        arg: dict | clouddrive.pb2.RenameFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def RenameFile(
        self, 
        arg: dict | clouddrive.pb2.RenameFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def RenameFile(
        self, 
        arg: dict | clouddrive.pb2.RenameFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        rename a single file

        ------------------- protobuf rpc definition --------------------

        // rename a single file
        rpc RenameFile(RenameFileRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message RenameFileRequest {
          string theFilePath = 1;
          string newName = 2;
        }
        """
        arg = to_message(clouddrive.pb2.RenameFileRequest, arg)
        if async_:
            return self.async_stub.RenameFile(arg, metadata=self.metadata)
        else:
            return self.stub.RenameFile(arg, metadata=self.metadata)

    @overload
    def RenameFiles(
        self, 
        arg: dict | clouddrive.pb2.RenameFilesRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def RenameFiles(
        self, 
        arg: dict | clouddrive.pb2.RenameFilesRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def RenameFiles(
        self, 
        arg: dict | clouddrive.pb2.RenameFilesRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        batch rename files

        ------------------- protobuf rpc definition --------------------

        // batch rename files
        rpc RenameFiles(RenameFilesRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message RenameFileRequest {
          string theFilePath = 1;
          string newName = 2;
        }
        message RenameFilesRequest { repeated RenameFileRequest renameFiles = 1; }
        """
        arg = to_message(clouddrive.pb2.RenameFilesRequest, arg)
        if async_:
            return self.async_stub.RenameFiles(arg, metadata=self.metadata)
        else:
            return self.stub.RenameFiles(arg, metadata=self.metadata)

    @overload
    def MoveFile(
        self, 
        arg: dict | clouddrive.pb2.MoveFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def MoveFile(
        self, 
        arg: dict | clouddrive.pb2.MoveFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def MoveFile(
        self, 
        arg: dict | clouddrive.pb2.MoveFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        move files to a dest folder

        ------------------- protobuf rpc definition --------------------

        // move files to a dest folder
        rpc MoveFile(MoveFileRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message MoveFileRequest {
          enum ConflictPolicy {
            Overwrite = 0;
            Rename = 1;
            Skip = 2;
          }
          repeated string theFilePaths = 1;
          string destPath = 2;
          optional ConflictPolicy conflictPolicy = 3;
          optional bool moveAcrossClouds = 4;
          // if true, apply recursive handling for folder-vs-folder conflicts
          optional bool handleConflictRecursively = 5;
        }
        """
        arg = to_message(clouddrive.pb2.MoveFileRequest, arg)
        if async_:
            return self.async_stub.MoveFile(arg, metadata=self.metadata)
        else:
            return self.stub.MoveFile(arg, metadata=self.metadata)

    @overload
    def CopyFile(
        self, 
        arg: dict | clouddrive.pb2.CopyFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def CopyFile(
        self, 
        arg: dict | clouddrive.pb2.CopyFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def CopyFile(
        self, 
        arg: dict | clouddrive.pb2.CopyFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        copy files to a dest folder

        ------------------- protobuf rpc definition --------------------

        // copy files to a dest folder
        rpc CopyFile(CopyFileRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message CopyFileRequest {
          enum ConflictPolicy {
            Overwrite = 0;
            Rename = 1;
            Skip = 2;
          }
          repeated string theFilePaths = 1;
          string destPath = 2;
          optional ConflictPolicy conflictPolicy = 3;
          optional bool handleConflictRecursively = 5;
        }
        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        """
        arg = to_message(clouddrive.pb2.CopyFileRequest, arg)
        if async_:
            return self.async_stub.CopyFile(arg, metadata=self.metadata)
        else:
            return self.stub.CopyFile(arg, metadata=self.metadata)

    @overload
    def DeleteFile(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def DeleteFile(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def DeleteFile(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        delete a single file

        ------------------- protobuf rpc definition --------------------

        // delete a single file
        rpc DeleteFile(FileRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.DeleteFile(arg, metadata=self.metadata)
        else:
            return self.stub.DeleteFile(arg, metadata=self.metadata)

    @overload
    def DeleteFilePermanently(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def DeleteFilePermanently(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def DeleteFilePermanently(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        delete a single file permanently, only aliyundrive supports this currently

        ------------------- protobuf rpc definition --------------------

        // delete a single file permanently, only aliyundrive supports this currently
        rpc DeleteFilePermanently(FileRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.DeleteFilePermanently(arg, metadata=self.metadata)
        else:
            return self.stub.DeleteFilePermanently(arg, metadata=self.metadata)

    @overload
    def DeleteFiles(
        self, 
        arg: dict | clouddrive.pb2.MultiFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def DeleteFiles(
        self, 
        arg: dict | clouddrive.pb2.MultiFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def DeleteFiles(
        self, 
        arg: dict | clouddrive.pb2.MultiFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        batch delete files

        ------------------- protobuf rpc definition --------------------

        // batch delete files
        rpc DeleteFiles(MultiFileRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message MultiFileRequest { repeated string path = 1; }
        """
        arg = to_message(clouddrive.pb2.MultiFileRequest, arg)
        if async_:
            return self.async_stub.DeleteFiles(arg, metadata=self.metadata)
        else:
            return self.stub.DeleteFiles(arg, metadata=self.metadata)

    @overload
    def DeleteFilesPermanently(
        self, 
        arg: dict | clouddrive.pb2.MultiFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def DeleteFilesPermanently(
        self, 
        arg: dict | clouddrive.pb2.MultiFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def DeleteFilesPermanently(
        self, 
        arg: dict | clouddrive.pb2.MultiFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        batch delete files permanently, only aliyundrive supports this currently

        ------------------- protobuf rpc definition --------------------

        // batch delete files permanently, only aliyundrive supports this currently
        rpc DeleteFilesPermanently(MultiFileRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message MultiFileRequest { repeated string path = 1; }
        """
        arg = to_message(clouddrive.pb2.MultiFileRequest, arg)
        if async_:
            return self.async_stub.DeleteFilesPermanently(arg, metadata=self.metadata)
        else:
            return self.stub.DeleteFilesPermanently(arg, metadata=self.metadata)

    @overload
    def AddOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.AddOfflineFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def AddOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.AddOfflineFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def AddOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.AddOfflineFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        add offline files by providing magnet, sha1, ..., applies only with folders
        with canOfflineDownload is true

        ------------------- protobuf rpc definition --------------------

        // add offline files by providing magnet, sha1, ..., applies only with folders
        // with canOfflineDownload is true
        rpc AddOfflineFiles(AddOfflineFileRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message AddOfflineFileRequest {
          string urls = 1;
          string toFolder = 2;
          optional uint64 checkFolderAfterSecs = 3; // auto check destination folder after these seconds to see if files are available
                                                    // 0 means no check
        }
        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        """
        arg = to_message(clouddrive.pb2.AddOfflineFileRequest, arg)
        if async_:
            return self.async_stub.AddOfflineFiles(arg, metadata=self.metadata)
        else:
            return self.stub.AddOfflineFiles(arg, metadata=self.metadata)

    @overload
    def RemoveOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.RemoveOfflineFilesRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def RemoveOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.RemoveOfflineFilesRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def RemoveOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.RemoveOfflineFilesRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        remove offline files by info hash

        ------------------- protobuf rpc definition --------------------

        // remove offline files by info hash
        rpc RemoveOfflineFiles(RemoveOfflineFilesRequest)
            returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message RemoveOfflineFilesRequest {
          string cloudName = 1;
          string cloudAccountId = 2;
          bool deleteFiles = 3;
          repeated string infoHashes = 4;
          optional string path = 5;
        }
        """
        arg = to_message(clouddrive.pb2.RemoveOfflineFilesRequest, arg)
        if async_:
            return self.async_stub.RemoveOfflineFiles(arg, metadata=self.metadata)
        else:
            return self.stub.RemoveOfflineFiles(arg, metadata=self.metadata)

    @overload
    def ListOfflineFilesByPath(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.OfflineFileListResult:
        ...
    @overload
    def ListOfflineFilesByPath(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.OfflineFileListResult]:
        ...
    def ListOfflineFilesByPath(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.OfflineFileListResult | Coroutine[Any, Any, clouddrive.pb2.OfflineFileListResult]:
        """
        list offline files

        ------------------- protobuf rpc definition --------------------

        // list offline files
        rpc ListOfflineFilesByPath(FileRequest) returns (OfflineFileListResult) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        message OfflineFile {
          string name = 1;
          uint64 size = 2;
          string url = 3;
          OfflineFileStatus status = 4;
          string infoHash = 5;
          string fileId = 6;
          uint64 add_time = 7;
          string parentId = 8;
          double percendDone = 9;
          uint64 peers = 10;
        }
        message OfflineFileListResult {
          repeated OfflineFile offlineFiles = 1;
          OfflineStatus status = 2;
        }
        message OfflineStatus {
          uint32 quota = 1;
          uint32 total = 2;
        }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.ListOfflineFilesByPath(arg, metadata=self.metadata)
        else:
            return self.stub.ListOfflineFilesByPath(arg, metadata=self.metadata)

    @overload
    def ListAllOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.OfflineFileListAllRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.OfflineFileListAllResult:
        ...
    @overload
    def ListAllOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.OfflineFileListAllRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.OfflineFileListAllResult]:
        ...
    def ListAllOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.OfflineFileListAllRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.OfflineFileListAllResult | Coroutine[Any, Any, clouddrive.pb2.OfflineFileListAllResult]:
        """
        list all offline files of a cloud with pagination

        ------------------- protobuf rpc definition --------------------

        // list all offline files of a cloud with pagination
        rpc ListAllOfflineFiles(OfflineFileListAllRequest)
            returns (OfflineFileListAllResult) {}

        ------------------- protobuf type definition -------------------

        message OfflineFile {
          string name = 1;
          uint64 size = 2;
          string url = 3;
          OfflineFileStatus status = 4;
          string infoHash = 5;
          string fileId = 6;
          uint64 add_time = 7;
          string parentId = 8;
          double percendDone = 9;
          uint64 peers = 10;
        }
        message OfflineFileListAllRequest {
          string cloudName = 1;
          string cloudAccountId = 2;
          uint32 page = 3;
          optional string path = 4;
        }
        message OfflineFileListAllResult {
          uint32 pageNo = 1;
          uint32 pageRowCount = 2;
          uint32 pageCount = 3;
          uint32 totalCount = 4;
          OfflineStatus status = 5;
          repeated OfflineFile offlineFiles = 6;
        }
        message OfflineStatus {
          uint32 quota = 1;
          uint32 total = 2;
        }
        """
        arg = to_message(clouddrive.pb2.OfflineFileListAllRequest, arg)
        if async_:
            return self.async_stub.ListAllOfflineFiles(arg, metadata=self.metadata)
        else:
            return self.stub.ListAllOfflineFiles(arg, metadata=self.metadata)

    @overload
    def GetOfflineQuotaInfo(
        self, 
        arg: dict | clouddrive.pb2.OfflineQuotaRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.OfflineQuotaInfo:
        ...
    @overload
    def GetOfflineQuotaInfo(
        self, 
        arg: dict | clouddrive.pb2.OfflineQuotaRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.OfflineQuotaInfo]:
        ...
    def GetOfflineQuotaInfo(
        self, 
        arg: dict | clouddrive.pb2.OfflineQuotaRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.OfflineQuotaInfo | Coroutine[Any, Any, clouddrive.pb2.OfflineQuotaInfo]:
        """
        get offline quota info of a cloud

        ------------------- protobuf rpc definition --------------------

        // get offline quota info of a cloud
        rpc GetOfflineQuotaInfo(OfflineQuotaRequest) returns (OfflineQuotaInfo) {}

        ------------------- protobuf type definition -------------------

        message OfflineQuotaInfo {
          int32 total = 1;
          int32 used = 2;
          int32 left = 3;
        }
        message OfflineQuotaRequest {
          string cloudName = 1;
          string cloudAccountId = 2;
          optional string path = 3;
        }
        """
        arg = to_message(clouddrive.pb2.OfflineQuotaRequest, arg)
        if async_:
            return self.async_stub.GetOfflineQuotaInfo(arg, metadata=self.metadata)
        else:
            return self.stub.GetOfflineQuotaInfo(arg, metadata=self.metadata)

    @overload
    def ClearOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.ClearOfflineFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ClearOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.ClearOfflineFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ClearOfflineFiles(
        self, 
        arg: dict | clouddrive.pb2.ClearOfflineFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        clear offline downloads by filter type: All, Finished, Error, Downloading

        ------------------- protobuf rpc definition --------------------

        // clear offline downloads by filter type: All, Finished, Error, Downloading
        rpc ClearOfflineFiles(ClearOfflineFileRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message ClearOfflineFileRequest {
          enum Filter {
            All = 0;
            Finished = 1;
            Error = 2;
            Downloading = 3;
          }
          string cloudName = 1;
          string cloudAccountId = 2;
          Filter filter = 3;
          bool deleteFiles = 4;
          optional string path = 5;
        }
        """
        if async_:
            async def request():
                await self.async_stub.ClearOfflineFiles(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ClearOfflineFiles(arg, metadata=self.metadata)
            return None

    @overload
    def RestartOfflineTask(
        self, 
        arg: dict | clouddrive.pb2.RestartOfflineFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RestartOfflineTask(
        self, 
        arg: dict | clouddrive.pb2.RestartOfflineFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RestartOfflineTask(
        self, 
        arg: dict | clouddrive.pb2.RestartOfflineFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        restart an offline download task by info hash, url and parent id

        ------------------- protobuf rpc definition --------------------

        // restart an offline download task by info hash, url and parent id
        rpc RestartOfflineTask(RestartOfflineFileRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message RestartOfflineFileRequest {
          string cloudName = 1;
          string cloudAccountId = 2;
          string infoHash = 3;
          string url = 4;
          string parentId = 5;
          optional string path = 6;
        }
        """
        if async_:
            async def request():
                await self.async_stub.RestartOfflineTask(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RestartOfflineTask(arg, metadata=self.metadata)
            return None

    @overload
    def AddSharedLink(
        self, 
        arg: dict | clouddrive.pb2.AddSharedLinkRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def AddSharedLink(
        self, 
        arg: dict | clouddrive.pb2.AddSharedLinkRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def AddSharedLink(
        self, 
        arg: dict | clouddrive.pb2.AddSharedLinkRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        add shared link to a folder

        ------------------- protobuf rpc definition --------------------

        // add shared link to a folder
        rpc AddSharedLink(AddSharedLinkRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message AddSharedLinkRequest {
          string sharedLinkUrl = 1;
          optional string sharedPassword = 2;
          string toFolder = 3;
        }
        """
        if async_:
            async def request():
                await self.async_stub.AddSharedLink(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.AddSharedLink(arg, metadata=self.metadata)
            return None

    @overload
    def GetFileDetailProperties(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileDetailProperties:
        ...
    @overload
    def GetFileDetailProperties(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileDetailProperties]:
        ...
    def GetFileDetailProperties(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileDetailProperties | Coroutine[Any, Any, clouddrive.pb2.FileDetailProperties]:
        """
        get folder properties, applies only with folders with hasDetailProperties
        is true

        ------------------- protobuf rpc definition --------------------

        // get folder properties, applies only with folders with hasDetailProperties
        // is true
        rpc GetFileDetailProperties(FileRequest) returns (FileDetailProperties) {}

        ------------------- protobuf type definition -------------------

        message FileDetailProperties {
          int64 totalFileCount = 1;
          int64 totalFolderCount = 2;
          int64 totalSize = 3;
          bool isFaved = 4;
          bool isShared = 5;
          string originalPath = 6;
        }
        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.GetFileDetailProperties(arg, metadata=self.metadata)
        else:
            return self.stub.GetFileDetailProperties(arg, metadata=self.metadata)

    @overload
    def GetSpaceInfo(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.SpaceInfo:
        ...
    @overload
    def GetSpaceInfo(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.SpaceInfo]:
        ...
    def GetSpaceInfo(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.SpaceInfo | Coroutine[Any, Any, clouddrive.pb2.SpaceInfo]:
        """
        get total/free/used space of a cloud path

        ------------------- protobuf rpc definition --------------------

        // get total/free/used space of a cloud path
        rpc GetSpaceInfo(FileRequest) returns (SpaceInfo) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        message SpaceInfo {
          int64 totalSpace = 1;
          int64 usedSpace = 2;
          int64 freeSpace = 3;
        }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.GetSpaceInfo(arg, metadata=self.metadata)
        else:
            return self.stub.GetSpaceInfo(arg, metadata=self.metadata)

    @overload
    def GetCloudMemberships(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CloudMemberships:
        ...
    @overload
    def GetCloudMemberships(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CloudMemberships]:
        ...
    def GetCloudMemberships(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CloudMemberships | Coroutine[Any, Any, clouddrive.pb2.CloudMemberships]:
        """
        get cloud account memberships

        ------------------- protobuf rpc definition --------------------

        // get cloud account memberships
        rpc GetCloudMemberships(FileRequest) returns (CloudMemberships) {}

        ------------------- protobuf type definition -------------------

        message CloudMembership {
          string identity = 1;
          optional google.protobuf.Timestamp expireTime = 2;
          optional string level = 3;
        }
        message CloudMemberships { repeated CloudMembership memberships = 1; }
        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.GetCloudMemberships(arg, metadata=self.metadata)
        else:
            return self.stub.GetCloudMemberships(arg, metadata=self.metadata)

    @overload
    def GetRuntimeInfo(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.RuntimeInfo:
        ...
    @overload
    def GetRuntimeInfo(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.RuntimeInfo]:
        ...
    def GetRuntimeInfo(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.RuntimeInfo | Coroutine[Any, Any, clouddrive.pb2.RuntimeInfo]:
        """
        get server runtime info

        ------------------- protobuf rpc definition --------------------

        // get server runtime info
        rpc GetRuntimeInfo(google.protobuf.Empty) returns (RuntimeInfo) {}

        ------------------- protobuf type definition -------------------

        message RuntimeInfo {
          string productName = 1;
          string productVersion = 2;
          string CloudAPIVersion = 3;
          string osInfo = 4;
        }
        """
        if async_:
            return self.async_stub.GetRuntimeInfo(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetRuntimeInfo(Empty(), metadata=self.metadata)

    @overload
    def GetFileBufferDiskCacheStats(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileBufferDiskCacheStats:
        ...
    @overload
    def GetFileBufferDiskCacheStats(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileBufferDiskCacheStats]:
        ...
    def GetFileBufferDiskCacheStats(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileBufferDiskCacheStats | Coroutine[Any, Any, clouddrive.pb2.FileBufferDiskCacheStats]:
        """
        file buffer disk cache runtime stats

        ------------------- protobuf rpc definition --------------------

        // file buffer disk cache runtime stats
        rpc GetFileBufferDiskCacheStats(google.protobuf.Empty) returns (FileBufferDiskCacheStats) {}

        ------------------- protobuf type definition -------------------

        // Eviction strategy for disk cache
        enum EvictionStrategy {
          LRU = 0; // Least Recently Used - evict entries not accessed recently
          LARGEST_FIRST = 1; // Evict largest files first to free space quickly
          SMALLEST_FIRST = 2; // Evict smallest files first to keep large files cached
        }
        // File buffer disk cache runtime stats
        message FileBufferDiskCacheStats {
          bool enabled = 1;
          uint64 totalBytes = 2;
          uint64 maxBytes = 3;
          uint64 entryCount = 4;
          uint64 segmentCount = 5;
          string rootDir = 6;
          bool scanCompleted = 7; // Whether initial disk scan has completed after restart
          EvictionStrategy evictionStrategy = 8; // Current active eviction strategy
        }
        """
        if async_:
            return self.async_stub.GetFileBufferDiskCacheStats(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetFileBufferDiskCacheStats(Empty(), metadata=self.metadata)

    @overload
    def PurgeFileBufferDiskCache(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def PurgeFileBufferDiskCache(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def PurgeFileBufferDiskCache(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        purge all disk-cached file buffers

        ------------------- protobuf rpc definition --------------------

        // purge all disk-cached file buffers
        rpc PurgeFileBufferDiskCache(google.protobuf.Empty) returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.PurgeFileBufferDiskCache(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.PurgeFileBufferDiskCache(Empty(), metadata=self.metadata)
            return None

    @overload
    def SetDiskCacheEvictionStrategy(
        self, 
        arg: dict | clouddrive.pb2.SetDiskCacheEvictionStrategyRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SetDiskCacheEvictionStrategy(
        self, 
        arg: dict | clouddrive.pb2.SetDiskCacheEvictionStrategyRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SetDiskCacheEvictionStrategy(
        self, 
        arg: dict | clouddrive.pb2.SetDiskCacheEvictionStrategyRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        set disk cache eviction strategy

        ------------------- protobuf rpc definition --------------------

        // set disk cache eviction strategy
        rpc SetDiskCacheEvictionStrategy(SetDiskCacheEvictionStrategyRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        // Eviction strategy for disk cache
        enum EvictionStrategy {
          LRU = 0; // Least Recently Used - evict entries not accessed recently
          LARGEST_FIRST = 1; // Evict largest files first to free space quickly
          SMALLEST_FIRST = 2; // Evict smallest files first to keep large files cached
        }
        // Request to set disk cache eviction strategy
        message SetDiskCacheEvictionStrategyRequest {
          EvictionStrategy strategy = 1;
        }
        """
        if async_:
            async def request():
                await self.async_stub.SetDiskCacheEvictionStrategy(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SetDiskCacheEvictionStrategy(arg, metadata=self.metadata)
            return None

    @overload
    def SetFolderDiskCache(
        self, 
        arg: dict | clouddrive.pb2.SetFolderDiskCacheRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SetFolderDiskCache(
        self, 
        arg: dict | clouddrive.pb2.SetFolderDiskCacheRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SetFolderDiskCache(
        self, 
        arg: dict | clouddrive.pb2.SetFolderDiskCacheRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        enable file buffer disk cache for a folder

        ------------------- protobuf rpc definition --------------------

        // enable file buffer disk cache for a folder
        rpc SetFolderDiskCache(SetFolderDiskCacheRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        // Extension filter mode for disk cache rules
        enum ExtensionFilterMode {
          EXTENSION_FILTER_DISABLED = 0; // No extension filtering
          EXTENSION_FILTER_INCLUDE = 1; // Only cache files with listed extensions
          EXTENSION_FILTER_EXCLUDE = 2; // Cache all files except those with listed extensions
        }
        // Request to set disk cache rules for a folder
        message SetFolderDiskCacheRequest {
          string path = 1;
          uint64 maxFileSize = 2; // 0 = no limit
          uint64 minFileSize = 3; // 0 = no minimum
          ExtensionFilterMode extensionFilterMode = 4;
          repeated string extensions = 5; // without dot, lowercase (e.g. \"mp4\", \"mkv\")
          bool enabled = 6; // true = enable cache, false = explicitly disable (blocks parent inheritance)
        }
        """
        if async_:
            async def request():
                await self.async_stub.SetFolderDiskCache(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SetFolderDiskCache(arg, metadata=self.metadata)
            return None

    @overload
    def RemoveFolderDiskCache(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RemoveFolderDiskCache(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RemoveFolderDiskCache(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        disable file buffer disk cache for a folder

        ------------------- protobuf rpc definition --------------------

        // disable file buffer disk cache for a folder
        rpc RemoveFolderDiskCache(FileRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        if async_:
            async def request():
                await self.async_stub.RemoveFolderDiskCache(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RemoveFolderDiskCache(arg, metadata=self.metadata)
            return None

    @overload
    def ListDiskCacheFolders(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.ListDiskCacheFoldersReply:
        ...
    @overload
    def ListDiskCacheFolders(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.ListDiskCacheFoldersReply]:
        ...
    def ListDiskCacheFolders(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.ListDiskCacheFoldersReply | Coroutine[Any, Any, clouddrive.pb2.ListDiskCacheFoldersReply]:
        """
        list all folders with disk cache enabled

        ------------------- protobuf rpc definition --------------------

        // list all folders with disk cache enabled
        rpc ListDiskCacheFolders(google.protobuf.Empty) returns (ListDiskCacheFoldersReply) {}

        ------------------- protobuf type definition -------------------

        // A folder with disk cache rules
        message DiskCacheFolder {
          string path = 1;
          uint64 maxFileSize = 2;
          uint64 minFileSize = 3;
          ExtensionFilterMode extensionFilterMode = 4;
          repeated string extensions = 5;
          bool enabled = 6;
        }
        // List of folders with disk cache enabled
        message ListDiskCacheFoldersReply {
          repeated DiskCacheFolder folders = 1;
        }
        """
        if async_:
            return self.async_stub.ListDiskCacheFolders(Empty(), metadata=self.metadata)
        else:
            return self.stub.ListDiskCacheFolders(Empty(), metadata=self.metadata)

    @overload
    def PrefetchFileRanges(
        self, 
        arg: dict | clouddrive.pb2.PrefetchFileRangesRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.PrefetchFileRangesReply:
        ...
    @overload
    def PrefetchFileRanges(
        self, 
        arg: dict | clouddrive.pb2.PrefetchFileRangesRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.PrefetchFileRangesReply]:
        ...
    def PrefetchFileRanges(
        self, 
        arg: dict | clouddrive.pb2.PrefetchFileRangesRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.PrefetchFileRangesReply | Coroutine[Any, Any, clouddrive.pb2.PrefetchFileRangesReply]:
        """
        client-driven cache hints: tell the server to prefetch byte ranges ahead of
        actual reads, with a priority that also triages concurrent work

        ------------------- protobuf rpc definition --------------------

        // client-driven cache hints: tell the server to prefetch byte ranges ahead of
        // actual reads, with a priority that also triages concurrent work
        rpc PrefetchFileRanges(PrefetchFileRangesRequest) returns (PrefetchFileRangesReply) {}

        ------------------- protobuf type definition -------------------

        message ByteRange {
          uint64 start = 1;  // inclusive
          uint64 length = 2; // bytes
        }
        // Priority of a client-driven cache hint or a Range read.
        // HIGH is served before NORMAL, NORMAL before LOW. LOW is used for
        // best-effort prefetch (e.g. thumbnail batches) that should not
        // stall the main playback read stream.
        enum HintPriority {
          HINT_PRIORITY_LOW = 0;
          HINT_PRIORITY_NORMAL = 1;
          HINT_PRIORITY_HIGH = 2;
        }
        message PrefetchFileRangesReply {
          uint64 hint_id = 1;
          uint32 accepted_range_count = 2;
          // ranges dropped for being out-of-bounds or already fully cached
          uint32 rejected_range_count = 3;
        }
        message PrefetchFileRangesRequest {
          string path = 1;
          repeated ByteRange ranges = 2;
          HintPriority priority = 3;
          // 0 = server allocates and returns an id
          uint64 hint_id = 4;
          // 0 = server default (clamped to [1, PREFETCH_HINT_TTL_SEC])
          uint32 ttl_seconds = 5;
          // if true, cancel any prior hints on this path before adding
          bool replace_existing = 6;
        }
        """
        arg = to_message(clouddrive.pb2.PrefetchFileRangesRequest, arg)
        if async_:
            return self.async_stub.PrefetchFileRanges(arg, metadata=self.metadata)
        else:
            return self.stub.PrefetchFileRanges(arg, metadata=self.metadata)

    @overload
    def CancelFilePrefetch(
        self, 
        arg: dict | clouddrive.pb2.CancelFilePrefetchRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def CancelFilePrefetch(
        self, 
        arg: dict | clouddrive.pb2.CancelFilePrefetchRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def CancelFilePrefetch(
        self, 
        arg: dict | clouddrive.pb2.CancelFilePrefetchRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        cancel one or more hints previously registered via PrefetchFileRanges

        ------------------- protobuf rpc definition --------------------

        // cancel one or more hints previously registered via PrefetchFileRanges
        rpc CancelFilePrefetch(CancelFilePrefetchRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message CancelFilePrefetchRequest {
          string path = 1;
          // empty = cancel all hints on that path
          repeated uint64 hint_ids = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.CancelFilePrefetch(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.CancelFilePrefetch(arg, metadata=self.metadata)
            return None

    @overload
    def CloseFileReader(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def CloseFileReader(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def CloseFileReader(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        Tell the server: \"I won't read this file again — drop the EntryReader
        (download buffers + downloader threads) as soon as no open handles
        remain, skipping the default 2-second post-close retention window that
        serves rapid close/reopen patterns from mounted filesystems. Use for
        web thumbnail generation, one-shot metadata probes, and any client that
        can guarantee it won't re-open the file in the near future.\"

        ------------------- protobuf rpc definition --------------------

        // Tell the server: \"I won't read this file again — drop the EntryReader
        // (download buffers + downloader threads) as soon as no open handles
        // remain, skipping the default 2-second post-close retention window that
        // serves rapid close/reopen patterns from mounted filesystems. Use for
        // web thumbnail generation, one-shot metadata probes, and any client that
        // can guarantee it won't re-open the file in the near future.\"
        rpc CloseFileReader(FileRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        if async_:
            async def request():
                await self.async_stub.CloseFileReader(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.CloseFileReader(arg, metadata=self.metadata)
            return None

    @overload
    def GetActivePrefetchHints(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetActivePrefetchHintsReply:
        ...
    @overload
    def GetActivePrefetchHints(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetActivePrefetchHintsReply]:
        ...
    def GetActivePrefetchHints(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetActivePrefetchHintsReply | Coroutine[Any, Any, clouddrive.pb2.GetActivePrefetchHintsReply]:
        """
        diagnostic: list currently-registered prefetch hints and cumulative
        telemetry counters (since process start)

        ------------------- protobuf rpc definition --------------------

        // diagnostic: list currently-registered prefetch hints and cumulative
        // telemetry counters (since process start)
        rpc GetActivePrefetchHints(google.protobuf.Empty) returns (GetActivePrefetchHintsReply) {}

        ------------------- protobuf type definition -------------------

        message ActivePrefetchHint {
          string path = 1;
          uint64 hint_id = 2;
          HintPriority priority = 3;
          uint64 total_bytes = 4;
          uint32 seconds_since_created = 5;
          uint32 remaining_ttl_seconds = 6;
          uint32 event_count = 7;
        }
        // Diagnostic snapshot + process-lifetime counters for the prefetch system.
        message GetActivePrefetchHintsReply {
          repeated ActivePrefetchHint hints = 1;
          uint64 hints_created_total = 2;
          uint64 hints_cancelled_total = 3;
          uint64 hints_expired_total = 4;
          uint64 ranges_rejected_cache_hit_total = 5;
          uint64 scale_up_events_total = 6;
          uint64 preempt_events_total = 7;
        }
        """
        if async_:
            return self.async_stub.GetActivePrefetchHints(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetActivePrefetchHints(Empty(), metadata=self.metadata)

    @overload
    def GetRunningInfo(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.RunInfo:
        ...
    @overload
    def GetRunningInfo(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.RunInfo]:
        ...
    def GetRunningInfo(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.RunInfo | Coroutine[Any, Any, clouddrive.pb2.RunInfo]:
        """
        get server stats, including cpu/mem/uptime

        ------------------- protobuf rpc definition --------------------

        // get server stats, including cpu/mem/uptime
        rpc GetRunningInfo(google.protobuf.Empty) returns (RunInfo) {}

        ------------------- protobuf type definition -------------------

        message RunInfo {
          double cpuUsage = 1;
          uint64 memUsageKB = 2;
          double uptime = 3;
          uint64 fhTableCount = 4;
          uint64 dirCacheCount = 5;
          uint64 tempFileCount = 6;
          uint64 dbDirCacheCount = 7;
          double downloadBytesPerSecond = 8;
          double uploadBytesPerSecond = 9;
          uint64 totalMemoryKB = 10;
        }
        """
        if async_:
            return self.async_stub.GetRunningInfo(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetRunningInfo(Empty(), metadata=self.metadata)

    @overload
    def GetOpenFileHandles(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.OpenFileHandleList:
        ...
    @overload
    def GetOpenFileHandles(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.OpenFileHandleList]:
        ...
    def GetOpenFileHandles(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.OpenFileHandleList | Coroutine[Any, Any, clouddrive.pb2.OpenFileHandleList]:
        """
        get all opened file handles

        ------------------- protobuf rpc definition --------------------

        // get all opened file handles
        rpc GetOpenFileHandles(google.protobuf.Empty) returns (OpenFileHandleList) {}

        ------------------- protobuf type definition -------------------

        message OpenFileHandle {
          uint64 fileHandle = 1;
          uint64 processId = 2;
          string processPath = 3;
          string filePath = 4;
          bool isDirectory = 5;
          google.protobuf.Timestamp openTime = 6; // open time
          optional string specialCommand =
              7; // special open command by clouddrive it self, such as \"\"
        }
        message OpenFileHandleList { repeated OpenFileHandle openFileHandles = 1; }
        """
        if async_:
            return self.async_stub.GetOpenFileHandles(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetOpenFileHandles(Empty(), metadata=self.metadata)

    @overload
    def Logout(
        self, 
        arg: dict | clouddrive.pb2.UserLogoutRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def Logout(
        self, 
        arg: dict | clouddrive.pb2.UserLogoutRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def Logout(
        self, 
        arg: dict | clouddrive.pb2.UserLogoutRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        logout from cloudfs server

        ------------------- protobuf rpc definition --------------------

        // logout from cloudfs server
        rpc Logout(UserLogoutRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message UserLogoutRequest { bool logoutFromCloudFS = 1; }
        """
        arg = to_message(clouddrive.pb2.UserLogoutRequest, arg)
        if async_:
            return self.async_stub.Logout(arg, metadata=self.metadata)
        else:
            return self.stub.Logout(arg, metadata=self.metadata)

    @overload
    def CanAddMoreMountPoints(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def CanAddMoreMountPoints(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def CanAddMoreMountPoints(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        check if current user can add more mount point

        ------------------- protobuf rpc definition --------------------

        // check if current user can add more mount point
        rpc CanAddMoreMountPoints(google.protobuf.Empty)
            returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        """
        if async_:
            return self.async_stub.CanAddMoreMountPoints(Empty(), metadata=self.metadata)
        else:
            return self.stub.CanAddMoreMountPoints(Empty(), metadata=self.metadata)

    @overload
    def GetMountPoints(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetMountPointsResult:
        ...
    @overload
    def GetMountPoints(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetMountPointsResult]:
        ...
    def GetMountPoints(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetMountPointsResult | Coroutine[Any, Any, clouddrive.pb2.GetMountPointsResult]:
        """
        get all mount points

        ------------------- protobuf rpc definition --------------------

        // get all mount points
        rpc GetMountPoints(google.protobuf.Empty) returns (GetMountPointsResult) {}

        ------------------- protobuf type definition -------------------

        message GetMountPointsResult { repeated MountPoint mountPoints = 1; }
        message MountPoint {
          string mountPoint = 1;
          string sourceDir = 2;
          bool localMount = 3;
          bool readOnly = 4;
          bool autoMount = 5;
          uint32 uid = 6;
          uint32 gid = 7;
          string permissions = 8;
          bool isMounted = 9;
          string failReason = 10;
          // Volume label used on Windows drive-letter mounts (interpolated into the
          // WinFSP UNC path). On non-Windows mounts this is cosmetic — the last
          // component of mountPoint is what the user actually sees.
          string name = 11;
        }
        """
        if async_:
            return self.async_stub.GetMountPoints(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetMountPoints(Empty(), metadata=self.metadata)

    @overload
    def AddMountPoint(
        self, 
        arg: dict | clouddrive.pb2.MountOption, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.MountPointResult:
        ...
    @overload
    def AddMountPoint(
        self, 
        arg: dict | clouddrive.pb2.MountOption, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.MountPointResult]:
        ...
    def AddMountPoint(
        self, 
        arg: dict | clouddrive.pb2.MountOption, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.MountPointResult | Coroutine[Any, Any, clouddrive.pb2.MountPointResult]:
        """
        add a new mount point

        ------------------- protobuf rpc definition --------------------

        // add a new mount point
        rpc AddMountPoint(MountOption) returns (MountPointResult) {}

        ------------------- protobuf type definition -------------------

        message MountOption {
          string mountPoint = 1;
          string sourceDir = 2;
          bool localMount = 3;
          bool readOnly = 4;
          bool autoMount = 5;
          uint32 uid = 6;
          uint32 gid = 7;
          string permissions = 8;
          string name = 9;
        }
        message MountPointResult {
          bool success = 1;
          string failReason = 2;
        }
        """
        arg = to_message(clouddrive.pb2.MountOption, arg)
        if async_:
            return self.async_stub.AddMountPoint(arg, metadata=self.metadata)
        else:
            return self.stub.AddMountPoint(arg, metadata=self.metadata)

    @overload
    def RemoveMountPoint(
        self, 
        arg: dict | clouddrive.pb2.MountPointRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.MountPointResult:
        ...
    @overload
    def RemoveMountPoint(
        self, 
        arg: dict | clouddrive.pb2.MountPointRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.MountPointResult]:
        ...
    def RemoveMountPoint(
        self, 
        arg: dict | clouddrive.pb2.MountPointRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.MountPointResult | Coroutine[Any, Any, clouddrive.pb2.MountPointResult]:
        """
        remove a mountpoint

        ------------------- protobuf rpc definition --------------------

        // remove a mountpoint
        rpc RemoveMountPoint(MountPointRequest) returns (MountPointResult) {}

        ------------------- protobuf type definition -------------------

        message MountPointRequest { string MountPoint = 1; }
        message MountPointResult {
          bool success = 1;
          string failReason = 2;
        }
        """
        arg = to_message(clouddrive.pb2.MountPointRequest, arg)
        if async_:
            return self.async_stub.RemoveMountPoint(arg, metadata=self.metadata)
        else:
            return self.stub.RemoveMountPoint(arg, metadata=self.metadata)

    @overload
    def Mount(
        self, 
        arg: dict | clouddrive.pb2.MountPointRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.MountPointResult:
        ...
    @overload
    def Mount(
        self, 
        arg: dict | clouddrive.pb2.MountPointRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.MountPointResult]:
        ...
    def Mount(
        self, 
        arg: dict | clouddrive.pb2.MountPointRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.MountPointResult | Coroutine[Any, Any, clouddrive.pb2.MountPointResult]:
        """
        mount a mount point

        ------------------- protobuf rpc definition --------------------

        // mount a mount point
        rpc Mount(MountPointRequest) returns (MountPointResult) {}

        ------------------- protobuf type definition -------------------

        message MountPointRequest { string MountPoint = 1; }
        message MountPointResult {
          bool success = 1;
          string failReason = 2;
        }
        """
        arg = to_message(clouddrive.pb2.MountPointRequest, arg)
        if async_:
            return self.async_stub.Mount(arg, metadata=self.metadata)
        else:
            return self.stub.Mount(arg, metadata=self.metadata)

    @overload
    def Unmount(
        self, 
        arg: dict | clouddrive.pb2.MountPointRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.MountPointResult:
        ...
    @overload
    def Unmount(
        self, 
        arg: dict | clouddrive.pb2.MountPointRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.MountPointResult]:
        ...
    def Unmount(
        self, 
        arg: dict | clouddrive.pb2.MountPointRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.MountPointResult | Coroutine[Any, Any, clouddrive.pb2.MountPointResult]:
        """
        unmount a mount point

        ------------------- protobuf rpc definition --------------------

        // unmount a mount point
        rpc Unmount(MountPointRequest) returns (MountPointResult) {}

        ------------------- protobuf type definition -------------------

        message MountPointRequest { string MountPoint = 1; }
        message MountPointResult {
          bool success = 1;
          string failReason = 2;
        }
        """
        arg = to_message(clouddrive.pb2.MountPointRequest, arg)
        if async_:
            return self.async_stub.Unmount(arg, metadata=self.metadata)
        else:
            return self.stub.Unmount(arg, metadata=self.metadata)

    @overload
    def UpdateMountPoint(
        self, 
        arg: dict | clouddrive.pb2.UpdateMountPointRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.MountPointResult:
        ...
    @overload
    def UpdateMountPoint(
        self, 
        arg: dict | clouddrive.pb2.UpdateMountPointRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.MountPointResult]:
        ...
    def UpdateMountPoint(
        self, 
        arg: dict | clouddrive.pb2.UpdateMountPointRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.MountPointResult | Coroutine[Any, Any, clouddrive.pb2.MountPointResult]:
        """
        change mount point settings

        ------------------- protobuf rpc definition --------------------

        // change mount point settings
        rpc UpdateMountPoint(UpdateMountPointRequest) returns (MountPointResult) {}

        ------------------- protobuf type definition -------------------

        message MountOption {
          string mountPoint = 1;
          string sourceDir = 2;
          bool localMount = 3;
          bool readOnly = 4;
          bool autoMount = 5;
          uint32 uid = 6;
          uint32 gid = 7;
          string permissions = 8;
          string name = 9;
        }
        message MountPointResult {
          bool success = 1;
          string failReason = 2;
        }
        message UpdateMountPointRequest {
          string mountPoint = 1;
          MountOption newMountOption = 2;
        }
        """
        arg = to_message(clouddrive.pb2.UpdateMountPointRequest, arg)
        if async_:
            return self.async_stub.UpdateMountPoint(arg, metadata=self.metadata)
        else:
            return self.stub.UpdateMountPoint(arg, metadata=self.metadata)

    @overload
    def GetAvailableDriveLetters(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetAvailableDriveLettersResult:
        ...
    @overload
    def GetAvailableDriveLetters(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetAvailableDriveLettersResult]:
        ...
    def GetAvailableDriveLetters(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetAvailableDriveLettersResult | Coroutine[Any, Any, clouddrive.pb2.GetAvailableDriveLettersResult]:
        """
        get all unused drive letters from server's local storage, applies to
        windows only

        ------------------- protobuf rpc definition --------------------

        // get all unused drive letters from server's local storage, applies to
        // windows only
        rpc GetAvailableDriveLetters(google.protobuf.Empty)
            returns (GetAvailableDriveLettersResult) {}

        ------------------- protobuf type definition -------------------

        message GetAvailableDriveLettersResult { repeated string driveLetters = 1; }
        """
        if async_:
            return self.async_stub.GetAvailableDriveLetters(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetAvailableDriveLetters(Empty(), metadata=self.metadata)

    @overload
    def HasDriveLetters(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.HasDriveLettersResult:
        ...
    @overload
    def HasDriveLetters(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.HasDriveLettersResult]:
        ...
    def HasDriveLetters(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.HasDriveLettersResult | Coroutine[Any, Any, clouddrive.pb2.HasDriveLettersResult]:
        """
        check if server has driver letters, returns true only on windows

        ------------------- protobuf rpc definition --------------------

        // check if server has driver letters, returns true only on windows
        rpc HasDriveLetters(google.protobuf.Empty) returns (HasDriveLettersResult) {}

        ------------------- protobuf type definition -------------------

        message HasDriveLettersResult { bool hasDriveLetters = 1; }
        """
        if async_:
            return self.async_stub.HasDriveLetters(Empty(), metadata=self.metadata)
        else:
            return self.stub.HasDriveLetters(Empty(), metadata=self.metadata)

    @overload
    def CanMountBothLocalAndCloud(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.BoolResult:
        ...
    @overload
    def CanMountBothLocalAndCloud(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.BoolResult]:
        ...
    def CanMountBothLocalAndCloud(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.BoolResult | Coroutine[Any, Any, clouddrive.pb2.BoolResult]:
        """
        check if server can mount both local and cloud drives

        ------------------- protobuf rpc definition --------------------

        // check if server can mount both local and cloud drives
        rpc CanMountBothLocalAndCloud(google.protobuf.Empty) returns (BoolResult) {}

        ------------------- protobuf type definition -------------------

        message BoolResult { bool result = 1; }
        """
        if async_:
            return self.async_stub.CanMountBothLocalAndCloud(Empty(), metadata=self.metadata)
        else:
            return self.stub.CanMountBothLocalAndCloud(Empty(), metadata=self.metadata)

    @overload
    def LocalGetSubFiles(
        self, 
        arg: dict | clouddrive.pb2.LocalGetSubFilesRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.LocalGetSubFilesResult]:
        ...
    @overload
    def LocalGetSubFiles(
        self, 
        arg: dict | clouddrive.pb2.LocalGetSubFilesRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.LocalGetSubFilesResult]]:
        ...
    def LocalGetSubFiles(
        self, 
        arg: dict | clouddrive.pb2.LocalGetSubFilesRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.LocalGetSubFilesResult] | Coroutine[Any, Any, Iterable[clouddrive.pb2.LocalGetSubFilesResult]]:
        """
        get subfiles of a local path, used for adding mountpoint from web ui

        ------------------- protobuf rpc definition --------------------

        // get subfiles of a local path, used for adding mountpoint from web ui
        rpc LocalGetSubFiles(LocalGetSubFilesRequest)
            returns (stream LocalGetSubFilesResult) {}

        ------------------- protobuf type definition -------------------

        message LocalGetSubFilesRequest {
          string parentFolder = 1;
          bool folderOnly = 2;
          bool includeCloudDrive = 3;
          bool includeAvailableDrive = 4;
        }
        message LocalGetSubFilesResult { repeated string subFiles = 1; }
        """
        arg = to_message(clouddrive.pb2.LocalGetSubFilesRequest, arg)
        if async_:
            return self.async_stub.LocalGetSubFiles(arg, metadata=self.metadata)
        else:
            return self.stub.LocalGetSubFiles(arg, metadata=self.metadata)

    @overload
    def LocalCreateFolder(
        self, 
        arg: dict | clouddrive.pb2.LocalCreateFolderRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.LocalCreateFolderResult:
        ...
    @overload
    def LocalCreateFolder(
        self, 
        arg: dict | clouddrive.pb2.LocalCreateFolderRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.LocalCreateFolderResult]:
        ...
    def LocalCreateFolder(
        self, 
        arg: dict | clouddrive.pb2.LocalCreateFolderRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.LocalCreateFolderResult | Coroutine[Any, Any, clouddrive.pb2.LocalCreateFolderResult]:
        """
        create a folder on the local filesystem

        ------------------- protobuf rpc definition --------------------

        // create a folder on the local filesystem
        rpc LocalCreateFolder(LocalCreateFolderRequest) returns (LocalCreateFolderResult) {}

        ------------------- protobuf type definition -------------------

        message LocalCreateFolderRequest {
          string parentFolder = 1;
          string folderName = 2;
        }
        message LocalCreateFolderResult {
          bool success = 1;
          string errorMessage = 2;
          string createdPath = 3;
        }
        """
        arg = to_message(clouddrive.pb2.LocalCreateFolderRequest, arg)
        if async_:
            return self.async_stub.LocalCreateFolder(arg, metadata=self.metadata)
        else:
            return self.stub.LocalCreateFolder(arg, metadata=self.metadata)

    @overload
    def GetAllTasksCount(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetAllTasksCountResult:
        ...
    @overload
    def GetAllTasksCount(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetAllTasksCountResult]:
        ...
    def GetAllTasksCount(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetAllTasksCountResult | Coroutine[Any, Any, clouddrive.pb2.GetAllTasksCountResult]:
        """
        get all transfer tasks' count

        ------------------- protobuf rpc definition --------------------

        // get all transfer tasks' count
        rpc GetAllTasksCount(google.protobuf.Empty) returns (GetAllTasksCountResult) {
        }

        ------------------- protobuf type definition -------------------

        message GetAllTasksCountResult {
          uint32 downloadCount = 1;
          uint32 uploadCount = 2;
          uint32 copyTaskCount = 6;
          PushMessage pushMessage = 3;
          bool hasUpdate = 4;
          repeated UploadFileInfo uploadFileStatusChanges =
              5; // upload file status changed
        }
        message PushMessage { string clouddriveVersion = 1; }
        message UploadFileInfo {
          enum Status {
            WaitforPreprocessing = 0;
            Preprocessing = 1;
            Cancelled = 2;
            Transfer = 3;
            Pause = 4;
            Finish = 5;
            Skipped = 6;
            Inqueue = 7;
            Ignored = 8;
            Error = 9;
            FatalError = 10;
          }
          enum OperatorType {
            Mount = 0; // Mount means the file is being uploaded by mounted file system
                       // operations
            Copy = 1; // Copy means the file is being uploaded by a copy task
            BackupFile = 2; // BackupFile means the file is being
                              // uploaded by a backup task
            RemoteUpload = 3; // RemoteUpload means the file is being uploaded by a
                              // remote upload task
          }
          string key = 1;
          string destPath = 2;
          uint64 size = 3;
          uint64 transferedBytes = 4;
          string status = 5;
          string errorMessage = 6;
          OperatorType operatorType = 7;
          Status statusEnum = 8;
        }
        """
        if async_:
            return self.async_stub.GetAllTasksCount(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetAllTasksCount(Empty(), metadata=self.metadata)

    @overload
    def GetDownloadFileCount(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetDownloadFileCountResult:
        ...
    @overload
    def GetDownloadFileCount(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetDownloadFileCountResult]:
        ...
    def GetDownloadFileCount(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetDownloadFileCountResult | Coroutine[Any, Any, clouddrive.pb2.GetDownloadFileCountResult]:
        """
        get download tasks' count

        ------------------- protobuf rpc definition --------------------

        // get download tasks' count
        rpc GetDownloadFileCount(google.protobuf.Empty)
            returns (GetDownloadFileCountResult) {}

        ------------------- protobuf type definition -------------------

        message GetDownloadFileCountResult { uint32 fileCount = 1; }
        """
        if async_:
            return self.async_stub.GetDownloadFileCount(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetDownloadFileCount(Empty(), metadata=self.metadata)

    @overload
    def GetDownloadFileList(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetDownloadFileListResult:
        ...
    @overload
    def GetDownloadFileList(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetDownloadFileListResult]:
        ...
    def GetDownloadFileList(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetDownloadFileListResult | Coroutine[Any, Any, clouddrive.pb2.GetDownloadFileListResult]:
        """
        get all download tasks

        ------------------- protobuf rpc definition --------------------

        // get all download tasks
        rpc GetDownloadFileList(google.protobuf.Empty)
            returns (GetDownloadFileListResult) {}

        ------------------- protobuf type definition -------------------

        message DownloadFileInfo {
          string filePath = 1;
          uint64 fileLength = 2;
          uint64 totalBufferUsed = 3;
          uint32 downloadThreadCount = 4;
          repeated string process = 5;
          string detailDownloadInfo = 6;
          optional string lastDownloadError = 7;
          double bytesPerSecond = 8;
        }
        message GetDownloadFileListResult {
          double globalBytesPerSecond = 1;
          repeated DownloadFileInfo downloadFiles = 4;
        }
        """
        if async_:
            return self.async_stub.GetDownloadFileList(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetDownloadFileList(Empty(), metadata=self.metadata)

    @overload
    def GetUploadFileCount(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetUploadFileCountResult:
        ...
    @overload
    def GetUploadFileCount(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetUploadFileCountResult]:
        ...
    def GetUploadFileCount(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetUploadFileCountResult | Coroutine[Any, Any, clouddrive.pb2.GetUploadFileCountResult]:
        """
        get all upload tasks' count

        ------------------- protobuf rpc definition --------------------

        // get all upload tasks' count
        rpc GetUploadFileCount(google.protobuf.Empty)
            returns (GetUploadFileCountResult) {}

        ------------------- protobuf type definition -------------------

        message GetUploadFileCountResult { uint32 fileCount = 1; }
        """
        if async_:
            return self.async_stub.GetUploadFileCount(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetUploadFileCount(Empty(), metadata=self.metadata)

    @overload
    def GetUploadFileList(
        self, 
        arg: dict | clouddrive.pb2.GetUploadFileListRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetUploadFileListResult:
        ...
    @overload
    def GetUploadFileList(
        self, 
        arg: dict | clouddrive.pb2.GetUploadFileListRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetUploadFileListResult]:
        ...
    def GetUploadFileList(
        self, 
        arg: dict | clouddrive.pb2.GetUploadFileListRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetUploadFileListResult | Coroutine[Any, Any, clouddrive.pb2.GetUploadFileListResult]:
        """
        get upload tasks, paged by providing page number and items per page and
        file name filter

        ------------------- protobuf rpc definition --------------------

        // get upload tasks, paged by providing page number and items per page and
        // file name filter
        rpc GetUploadFileList(GetUploadFileListRequest)
            returns (GetUploadFileListResult) {}

        ------------------- protobuf type definition -------------------

        message GetUploadFileListRequest {
          bool getAll = 1;
          uint32 itemsPerPage = 2;
          uint32 pageNumber = 3;
          string filter = 4;
          optional UploadFileInfo.Status statusFilter = 5;
          optional UploadFileInfo.OperatorType operatorTypeFilter = 6;
        }
        message GetUploadFileListResult {
          uint32 totalCount = 1;
          repeated UploadFileInfo uploadFiles = 2;
          double globalBytesPerSecond = 3;
          uint64 totalBytes = 4;
          uint64 finishedBytes = 5;
          uint32 totalCountFiltered = 6;
        }
        message UploadFileInfo {
          enum Status {
            WaitforPreprocessing = 0;
            Preprocessing = 1;
            Cancelled = 2;
            Transfer = 3;
            Pause = 4;
            Finish = 5;
            Skipped = 6;
            Inqueue = 7;
            Ignored = 8;
            Error = 9;
            FatalError = 10;
          }
          enum OperatorType {
            Mount = 0; // Mount means the file is being uploaded by mounted file system
                       // operations
            Copy = 1; // Copy means the file is being uploaded by a copy task
            BackupFile = 2; // BackupFile means the file is being
                              // uploaded by a backup task
            RemoteUpload = 3; // RemoteUpload means the file is being uploaded by a
                              // remote upload task
          }
          string key = 1;
          string destPath = 2;
          uint64 size = 3;
          uint64 transferedBytes = 4;
          string status = 5;
          string errorMessage = 6;
          OperatorType operatorType = 7;
          Status statusEnum = 8;
        }
        """
        arg = to_message(clouddrive.pb2.GetUploadFileListRequest, arg)
        if async_:
            return self.async_stub.GetUploadFileList(arg, metadata=self.metadata)
        else:
            return self.stub.GetUploadFileList(arg, metadata=self.metadata)

    @overload
    def CancelAllUploadFiles(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def CancelAllUploadFiles(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def CancelAllUploadFiles(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        cancel all upload tasks

        ------------------- protobuf rpc definition --------------------

        // cancel all upload tasks
        rpc CancelAllUploadFiles(google.protobuf.Empty)
            returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.CancelAllUploadFiles(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.CancelAllUploadFiles(Empty(), metadata=self.metadata)
            return None

    @overload
    def CancelUploadFiles(
        self, 
        arg: dict | clouddrive.pb2.MultpleUploadFileKeyRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def CancelUploadFiles(
        self, 
        arg: dict | clouddrive.pb2.MultpleUploadFileKeyRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def CancelUploadFiles(
        self, 
        arg: dict | clouddrive.pb2.MultpleUploadFileKeyRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        cancel selected upload tasks

        ------------------- protobuf rpc definition --------------------

        // cancel selected upload tasks
        rpc CancelUploadFiles(MultpleUploadFileKeyRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message MultpleUploadFileKeyRequest { repeated string keys = 1; }

        // (removed) RapidUploadFileRequest / Response and CompleteRapidUpload* messages
        """
        if async_:
            async def request():
                await self.async_stub.CancelUploadFiles(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.CancelUploadFiles(arg, metadata=self.metadata)
            return None

    @overload
    def PauseAllUploadFiles(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def PauseAllUploadFiles(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def PauseAllUploadFiles(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        pause all upload tasks

        ------------------- protobuf rpc definition --------------------

        // pause all upload tasks
        rpc PauseAllUploadFiles(google.protobuf.Empty)
            returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.PauseAllUploadFiles(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.PauseAllUploadFiles(Empty(), metadata=self.metadata)
            return None

    @overload
    def PauseUploadFiles(
        self, 
        arg: dict | clouddrive.pb2.MultpleUploadFileKeyRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def PauseUploadFiles(
        self, 
        arg: dict | clouddrive.pb2.MultpleUploadFileKeyRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def PauseUploadFiles(
        self, 
        arg: dict | clouddrive.pb2.MultpleUploadFileKeyRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        pause selected upload tasks

        ------------------- protobuf rpc definition --------------------

        // pause selected upload tasks
        rpc PauseUploadFiles(MultpleUploadFileKeyRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message MultpleUploadFileKeyRequest { repeated string keys = 1; }

        // (removed) RapidUploadFileRequest / Response and CompleteRapidUpload* messages
        """
        if async_:
            async def request():
                await self.async_stub.PauseUploadFiles(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.PauseUploadFiles(arg, metadata=self.metadata)
            return None

    @overload
    def ResumeAllUploadFiles(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ResumeAllUploadFiles(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ResumeAllUploadFiles(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        resume all upload tasks

        ------------------- protobuf rpc definition --------------------

        // resume all upload tasks
        rpc ResumeAllUploadFiles(google.protobuf.Empty)
            returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.ResumeAllUploadFiles(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ResumeAllUploadFiles(Empty(), metadata=self.metadata)
            return None

    @overload
    def ResumeUploadFiles(
        self, 
        arg: dict | clouddrive.pb2.MultpleUploadFileKeyRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ResumeUploadFiles(
        self, 
        arg: dict | clouddrive.pb2.MultpleUploadFileKeyRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ResumeUploadFiles(
        self, 
        arg: dict | clouddrive.pb2.MultpleUploadFileKeyRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        resume selected upload tasks

        ------------------- protobuf rpc definition --------------------

        // resume selected upload tasks
        rpc ResumeUploadFiles(MultpleUploadFileKeyRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message MultpleUploadFileKeyRequest { repeated string keys = 1; }

        // (removed) RapidUploadFileRequest / Response and CompleteRapidUpload* messages
        """
        if async_:
            async def request():
                await self.async_stub.ResumeUploadFiles(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ResumeUploadFiles(arg, metadata=self.metadata)
            return None

    @overload
    def GetCopyTasks(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetCopyTaskResult:
        ...
    @overload
    def GetCopyTasks(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetCopyTaskResult]:
        ...
    def GetCopyTasks(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetCopyTaskResult | Coroutine[Any, Any, clouddrive.pb2.GetCopyTaskResult]:
        """
        get all system tasks

        ------------------- protobuf rpc definition --------------------

        // get all system tasks
        rpc GetCopyTasks(google.protobuf.Empty) returns (GetCopyTaskResult) {}

        ------------------- protobuf type definition -------------------

        message CopyTask {
          enum TaskMode {
            Copy = 0;
            Move = 1;
          }
          enum TaskStatus {
            Pending = 0;
            Scanning = 1;
            Scanned = 2;
            Completed = 3;
            Failed = 4;
          }
          TaskMode taskMode = 2;
          string sourcePath = 3;
          string destPath = 4;
          TaskStatus status = 5;
          uint64 totalFolders = 6;
          uint64 totalFiles = 7;
          uint64 failedFolders = 8;
          uint64 failedFiles = 9;
          uint64 uploadedFiles = 10;
          uint64 cancelledFiles = 11;
          uint64 skippedFiles = 16;
          uint64 totalBytes = 12;
          uint64 uploadedBytes = 13;
          bool paused = 14;
          repeated TaskError errors = 15;
          google.protobuf.Timestamp startTime = 17;
          optional google.protobuf.Timestamp endTime = 18;
        }
        message GetCopyTaskResult { repeated CopyTask copyTasks = 1; }
        """
        if async_:
            return self.async_stub.GetCopyTasks(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetCopyTasks(Empty(), metadata=self.metadata)

    @overload
    def GetMergeTasks(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetMergeTasksResult:
        ...
    @overload
    def GetMergeTasks(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetMergeTasksResult]:
        ...
    def GetMergeTasks(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetMergeTasksResult | Coroutine[Any, Any, clouddrive.pb2.GetMergeTasksResult]:
        """
        get all merge tasks (folder recursive merges)

        ------------------- protobuf rpc definition --------------------

        // get all merge tasks (folder recursive merges)
        rpc GetMergeTasks(google.protobuf.Empty) returns (GetMergeTasksResult) {}

        ------------------- protobuf type definition -------------------

        message GetMergeTasksResult { repeated MergeTask mergeTasks = 1; }
        // Merge tasks (for recursive folder merges triggered by request with
        // handleConflictRecursively=true)
        message MergeTask {
          enum TaskStatus {
            Pending = 0;
            Running = 1;
            Completed = 2;
            Failed = 3;
            Cancelled = 4;
          }
          enum OperationType {
            Move = 0;
            Copy = 1;
          }
          string sourcePath = 1;
          string destPath = 2;
          TaskStatus status = 3;
          uint64 mergedFiles = 4;
          uint64 mergedFolders = 5;
          google.protobuf.Timestamp startTime = 6;
          optional google.protobuf.Timestamp endTime = 7;
          optional string errorMessage = 8;
          // conflict policy used when this task was created
          MoveFileRequest.ConflictPolicy conflictPolicy = 9;
          // operation that created this merge task
          OperationType operationType = 10;
        }
        """
        if async_:
            return self.async_stub.GetMergeTasks(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetMergeTasks(Empty(), metadata=self.metadata)

    @overload
    def CancelMergeTask(
        self, 
        arg: dict | clouddrive.pb2.CancelMergeTaskRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def CancelMergeTask(
        self, 
        arg: dict | clouddrive.pb2.CancelMergeTaskRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def CancelMergeTask(
        self, 
        arg: dict | clouddrive.pb2.CancelMergeTaskRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        cancel a merge task by source and destination paths

        ------------------- protobuf rpc definition --------------------

        // cancel a merge task by source and destination paths
        rpc CancelMergeTask(CancelMergeTaskRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message CancelMergeTaskRequest {
          string sourcePath = 1;
          string destPath = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.CancelMergeTask(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.CancelMergeTask(arg, metadata=self.metadata)
            return None

    @overload
    def CancelCopyTask(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def CancelCopyTask(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def CancelCopyTask(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        cancel copy folder task

        ------------------- protobuf rpc definition --------------------

        // cancel copy folder task
        rpc CancelCopyTask(CopyTaskRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message CopyTaskRequest {
          string sourcePath = 1;
          string destPath = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.CancelCopyTask(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.CancelCopyTask(arg, metadata=self.metadata)
            return None

    @overload
    def PauseCopyTask(
        self, 
        arg: dict | clouddrive.pb2.PauseCopyTaskRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def PauseCopyTask(
        self, 
        arg: dict | clouddrive.pb2.PauseCopyTaskRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def PauseCopyTask(
        self, 
        arg: dict | clouddrive.pb2.PauseCopyTaskRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        pause copy folder task

        ------------------- protobuf rpc definition --------------------

        // pause copy folder task
        rpc PauseCopyTask(PauseCopyTaskRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message PauseCopyTaskRequest {
          string sourcePath = 1;
          string destPath = 2;
          bool pause = 3;
        }
        """
        if async_:
            async def request():
                await self.async_stub.PauseCopyTask(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.PauseCopyTask(arg, metadata=self.metadata)
            return None

    @overload
    def RestartCopyTask(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RestartCopyTask(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RestartCopyTask(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        restart copy folder task

        ------------------- protobuf rpc definition --------------------

        // restart copy folder task
        rpc RestartCopyTask(CopyTaskRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message CopyTaskRequest {
          string sourcePath = 1;
          string destPath = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.RestartCopyTask(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RestartCopyTask(arg, metadata=self.metadata)
            return None

    @overload
    def RemoveCompletedCopyTasks(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RemoveCompletedCopyTasks(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RemoveCompletedCopyTasks(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        remove all completed copy tasks

        ------------------- protobuf rpc definition --------------------

        // remove all completed copy tasks
        rpc RemoveCompletedCopyTasks(google.protobuf.Empty)
            returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.RemoveCompletedCopyTasks(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RemoveCompletedCopyTasks(Empty(), metadata=self.metadata)
            return None

    @overload
    def RemoveAllCopyTasks(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.BatchOperationResult:
        ...
    @overload
    def RemoveAllCopyTasks(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        ...
    def RemoveAllCopyTasks(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.BatchOperationResult | Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        """
        batch operations for copy tasks

        ------------------- protobuf rpc definition --------------------

        // batch operations for copy tasks
        rpc RemoveAllCopyTasks(google.protobuf.Empty) returns (BatchOperationResult) {
        }

        ------------------- protobuf type definition -------------------

        message BatchOperationResult {
          bool success = 1;
          uint32 affectedCount = 2;
          string errorMessage = 3;
        }
        """
        if async_:
            return self.async_stub.RemoveAllCopyTasks(Empty(), metadata=self.metadata)
        else:
            return self.stub.RemoveAllCopyTasks(Empty(), metadata=self.metadata)

    @overload
    def RemoveCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskBatchRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.BatchOperationResult:
        ...
    @overload
    def RemoveCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskBatchRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        ...
    def RemoveCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskBatchRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.BatchOperationResult | Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        """

        ------------------- protobuf rpc definition --------------------

        rpc RemoveCopyTasks(CopyTaskBatchRequest) returns (BatchOperationResult) {}

        ------------------- protobuf type definition -------------------

        message BatchOperationResult {
          bool success = 1;
          uint32 affectedCount = 2;
          string errorMessage = 3;
        }
        message CopyTaskBatchRequest {
          // Task key format: \"{sourcePath}:{destPath}\".
          // Build each key from the CopyTask returned by GetCopyTasks using the
          // exact sourcePath and destPath strings (no extra normalization).
          repeated string taskKeys = 1;
        }
        """
        arg = to_message(clouddrive.pb2.CopyTaskBatchRequest, arg)
        if async_:
            return self.async_stub.RemoveCopyTasks(arg, metadata=self.metadata)
        else:
            return self.stub.RemoveCopyTasks(arg, metadata=self.metadata)

    @overload
    def PauseAllCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.PauseAllCopyTasksRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.BatchOperationResult:
        ...
    @overload
    def PauseAllCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.PauseAllCopyTasksRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        ...
    def PauseAllCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.PauseAllCopyTasksRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.BatchOperationResult | Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        """

        ------------------- protobuf rpc definition --------------------

        rpc PauseAllCopyTasks(PauseAllCopyTasksRequest)
            returns (BatchOperationResult) {}

        ------------------- protobuf type definition -------------------

        message BatchOperationResult {
          bool success = 1;
          uint32 affectedCount = 2;
          string errorMessage = 3;
        }
        message PauseAllCopyTasksRequest { bool pause = 1; }
        """
        arg = to_message(clouddrive.pb2.PauseAllCopyTasksRequest, arg)
        if async_:
            return self.async_stub.PauseAllCopyTasks(arg, metadata=self.metadata)
        else:
            return self.stub.PauseAllCopyTasks(arg, metadata=self.metadata)

    @overload
    def PauseCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.PauseCopyTasksRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.BatchOperationResult:
        ...
    @overload
    def PauseCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.PauseCopyTasksRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        ...
    def PauseCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.PauseCopyTasksRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.BatchOperationResult | Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        """

        ------------------- protobuf rpc definition --------------------

        rpc PauseCopyTasks(PauseCopyTasksRequest) returns (BatchOperationResult) {}

        ------------------- protobuf type definition -------------------

        message BatchOperationResult {
          bool success = 1;
          uint32 affectedCount = 2;
          string errorMessage = 3;
        }
        message PauseCopyTasksRequest {
          repeated string taskKeys = 1;
          bool pause = 2;
        }
        """
        arg = to_message(clouddrive.pb2.PauseCopyTasksRequest, arg)
        if async_:
            return self.async_stub.PauseCopyTasks(arg, metadata=self.metadata)
        else:
            return self.stub.PauseCopyTasks(arg, metadata=self.metadata)

    @overload
    def ResumeAllCopyTasks(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.BatchOperationResult:
        ...
    @overload
    def ResumeAllCopyTasks(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        ...
    def ResumeAllCopyTasks(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.BatchOperationResult | Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        """

        ------------------- protobuf rpc definition --------------------

        rpc ResumeAllCopyTasks(google.protobuf.Empty) returns (BatchOperationResult) {
        }

        ------------------- protobuf type definition -------------------

        message BatchOperationResult {
          bool success = 1;
          uint32 affectedCount = 2;
          string errorMessage = 3;
        }
        """
        if async_:
            return self.async_stub.ResumeAllCopyTasks(Empty(), metadata=self.metadata)
        else:
            return self.stub.ResumeAllCopyTasks(Empty(), metadata=self.metadata)

    @overload
    def ResumeCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskBatchRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.BatchOperationResult:
        ...
    @overload
    def ResumeCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskBatchRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        ...
    def ResumeCopyTasks(
        self, 
        arg: dict | clouddrive.pb2.CopyTaskBatchRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.BatchOperationResult | Coroutine[Any, Any, clouddrive.pb2.BatchOperationResult]:
        """

        ------------------- protobuf rpc definition --------------------

        rpc ResumeCopyTasks(CopyTaskBatchRequest) returns (BatchOperationResult) {}

        ------------------- protobuf type definition -------------------

        message BatchOperationResult {
          bool success = 1;
          uint32 affectedCount = 2;
          string errorMessage = 3;
        }
        message CopyTaskBatchRequest {
          // Task key format: \"{sourcePath}:{destPath}\".
          // Build each key from the CopyTask returned by GetCopyTasks using the
          // exact sourcePath and destPath strings (no extra normalization).
          repeated string taskKeys = 1;
        }
        """
        arg = to_message(clouddrive.pb2.CopyTaskBatchRequest, arg)
        if async_:
            return self.async_stub.ResumeCopyTasks(arg, metadata=self.metadata)
        else:
            return self.stub.ResumeCopyTasks(arg, metadata=self.metadata)

    @overload
    def CanAddMoreCloudApis(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def CanAddMoreCloudApis(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def CanAddMoreCloudApis(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        check if current user can add more cloud apis

        ------------------- protobuf rpc definition --------------------

        // check if current user can add more cloud apis
        rpc CanAddMoreCloudApis(google.protobuf.Empty) returns (FileOperationResult) {
        }

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        """
        if async_:
            return self.async_stub.CanAddMoreCloudApis(Empty(), metadata=self.metadata)
        else:
            return self.stub.CanAddMoreCloudApis(Empty(), metadata=self.metadata)

    @overload
    def APILogin115Editthiscookie(
        self, 
        arg: dict | clouddrive.pb2.Login115EditthiscookieRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILogin115Editthiscookie(
        self, 
        arg: dict | clouddrive.pb2.Login115EditthiscookieRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILogin115Editthiscookie(
        self, 
        arg: dict | clouddrive.pb2.Login115EditthiscookieRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add 115 cloud with editthiscookie

        ------------------- protobuf rpc definition --------------------

        // add 115 cloud with editthiscookie
        rpc APILogin115Editthiscookie(Login115EditthiscookieRequest)
            returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message Login115EditthiscookieRequest { string editThiscookieString = 1; }
        """
        arg = to_message(clouddrive.pb2.Login115EditthiscookieRequest, arg)
        if async_:
            return self.async_stub.APILogin115Editthiscookie(arg, metadata=self.metadata)
        else:
            return self.stub.APILogin115Editthiscookie(arg, metadata=self.metadata)

    @overload
    def APILogin115QRCode(
        self, 
        arg: dict | clouddrive.pb2.Login115QrCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.QRCodeScanMessage]:
        ...
    @overload
    def APILogin115QRCode(
        self, 
        arg: dict | clouddrive.pb2.Login115QrCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.QRCodeScanMessage]]:
        ...
    def APILogin115QRCode(
        self, 
        arg: dict | clouddrive.pb2.Login115QrCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.QRCodeScanMessage] | Coroutine[Any, Any, Iterable[clouddrive.pb2.QRCodeScanMessage]]:
        """
        add 115 cloud with qr scanning

        ------------------- protobuf rpc definition --------------------

        // add 115 cloud with qr scanning
        rpc APILogin115QRCode(Login115QrCodeRequest)
            returns (stream QRCodeScanMessage) {}

        ------------------- protobuf type definition -------------------

        message Login115QrCodeRequest { optional string platformString = 1; }
        message QRCodeScanMessage {
          QRCodeScanMessageType messageType = 1;
          string message = 2;
        }
        enum QRCodeScanMessageType {
          SHOW_IMAGE = 0;
          SHOW_IMAGE_CONTENT = 1;
          CHANGE_STATUS = 2;
          CLOSE = 3;
          ERROR = 4;
        }
        """
        arg = to_message(clouddrive.pb2.Login115QrCodeRequest, arg)
        if async_:
            return self.async_stub.APILogin115QRCode(arg, metadata=self.metadata)
        else:
            return self.stub.APILogin115QRCode(arg, metadata=self.metadata)

    @overload
    def APILogin115OpenOAuth(
        self, 
        arg: dict | clouddrive.pb2.Login115OpenOAuthRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILogin115OpenOAuth(
        self, 
        arg: dict | clouddrive.pb2.Login115OpenOAuthRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILogin115OpenOAuth(
        self, 
        arg: dict | clouddrive.pb2.Login115OpenOAuthRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add 115 open with OAuth

        ------------------- protobuf rpc definition --------------------

        // add 115 open with OAuth
        rpc APILogin115OpenOAuth(Login115OpenOAuthRequest) returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message Login115OpenOAuthRequest {
          string refresh_token = 1;
          string access_token = 2;
          uint64 expires_in = 3;
          optional ProxyInfo apiProxy = 4;
          optional ProxyInfo dataProxy = 5;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.Login115OpenOAuthRequest, arg)
        if async_:
            return self.async_stub.APILogin115OpenOAuth(arg, metadata=self.metadata)
        else:
            return self.stub.APILogin115OpenOAuth(arg, metadata=self.metadata)

    @overload
    def APILogin115OpenQRCode(
        self, 
        arg: dict | clouddrive.pb2.Login115OpenQRCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.QRCodeScanMessage]:
        ...
    @overload
    def APILogin115OpenQRCode(
        self, 
        arg: dict | clouddrive.pb2.Login115OpenQRCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.QRCodeScanMessage]]:
        ...
    def APILogin115OpenQRCode(
        self, 
        arg: dict | clouddrive.pb2.Login115OpenQRCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.QRCodeScanMessage] | Coroutine[Any, Any, Iterable[clouddrive.pb2.QRCodeScanMessage]]:
        """
        add 115 open with qr scanning

        ------------------- protobuf rpc definition --------------------

        // add 115 open with qr scanning
        rpc APILogin115OpenQRCode(Login115OpenQRCodeRequest)
            returns (stream QRCodeScanMessage) {}

        ------------------- protobuf type definition -------------------

        message Login115OpenQRCodeRequest {
          optional ProxyInfo apiProxy = 1;
          optional ProxyInfo dataProxy = 2;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        message QRCodeScanMessage {
          QRCodeScanMessageType messageType = 1;
          string message = 2;
        }
        enum QRCodeScanMessageType {
          SHOW_IMAGE = 0;
          SHOW_IMAGE_CONTENT = 1;
          CHANGE_STATUS = 2;
          CLOSE = 3;
          ERROR = 4;
        }
        """
        arg = to_message(clouddrive.pb2.Login115OpenQRCodeRequest, arg)
        if async_:
            return self.async_stub.APILogin115OpenQRCode(arg, metadata=self.metadata)
        else:
            return self.stub.APILogin115OpenQRCode(arg, metadata=self.metadata)

    @overload
    def APILoginGuangYaPanQRCode(
        self, 
        arg: dict | clouddrive.pb2.LoginGuangYaPanQRCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.QRCodeScanMessage]:
        ...
    @overload
    def APILoginGuangYaPanQRCode(
        self, 
        arg: dict | clouddrive.pb2.LoginGuangYaPanQRCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.QRCodeScanMessage]]:
        ...
    def APILoginGuangYaPanQRCode(
        self, 
        arg: dict | clouddrive.pb2.LoginGuangYaPanQRCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.QRCodeScanMessage] | Coroutine[Any, Any, Iterable[clouddrive.pb2.QRCodeScanMessage]]:
        """
        add GuangYaPan with qr (device code) scanning

        ------------------- protobuf rpc definition --------------------

        // add GuangYaPan with qr (device code) scanning
        rpc APILoginGuangYaPanQRCode(LoginGuangYaPanQRCodeRequest)
            returns (stream QRCodeScanMessage) {}

        ------------------- protobuf type definition -------------------

        message LoginGuangYaPanQRCodeRequest {
          optional ProxyInfo apiProxy = 1;
          optional ProxyInfo dataProxy = 2;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        message QRCodeScanMessage {
          QRCodeScanMessageType messageType = 1;
          string message = 2;
        }
        enum QRCodeScanMessageType {
          SHOW_IMAGE = 0;
          SHOW_IMAGE_CONTENT = 1;
          CHANGE_STATUS = 2;
          CLOSE = 3;
          ERROR = 4;
        }
        """
        arg = to_message(clouddrive.pb2.LoginGuangYaPanQRCodeRequest, arg)
        if async_:
            return self.async_stub.APILoginGuangYaPanQRCode(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginGuangYaPanQRCode(arg, metadata=self.metadata)

    @overload
    def APILoginGuangYaPanOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginGuangYaPanOAuthRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginGuangYaPanOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginGuangYaPanOAuthRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginGuangYaPanOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginGuangYaPanOAuthRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add GuangYaPan with web PKCE (authorization code) result

        ------------------- protobuf rpc definition --------------------

        // add GuangYaPan with web PKCE (authorization code) result
        rpc APILoginGuangYaPanOAuth(LoginGuangYaPanOAuthRequest)
            returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        // GuangYaPan web PKCE: the oauth_callback redirect server performs the PKCE
        // token exchange and delivers ready-made tokens back to the app (same shape as
        // the other OAuth providers).
        message LoginGuangYaPanOAuthRequest {
          string refresh_token = 1;
          string access_token = 2;
          uint64 expires_in = 3;
          optional ProxyInfo apiProxy = 4;
          optional ProxyInfo dataProxy = 5;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginGuangYaPanOAuthRequest, arg)
        if async_:
            return self.async_stub.APILoginGuangYaPanOAuth(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginGuangYaPanOAuth(arg, metadata=self.metadata)

    @overload
    def APILoginAliyundriveOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginAliyundriveOAuthRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginAliyundriveOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginAliyundriveOAuthRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginAliyundriveOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginAliyundriveOAuthRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add AliyunDriveOpen with OAuth result

        ------------------- protobuf rpc definition --------------------

        // add AliyunDriveOpen with OAuth result
        rpc APILoginAliyundriveOAuth(LoginAliyundriveOAuthRequest)
            returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginAliyundriveOAuthRequest {
          string refresh_token = 1;
          string access_token = 2;
          uint64 expires_in = 3;
          optional ProxyInfo apiProxy = 4;
          optional ProxyInfo dataProxy = 5;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginAliyundriveOAuthRequest, arg)
        if async_:
            return self.async_stub.APILoginAliyundriveOAuth(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginAliyundriveOAuth(arg, metadata=self.metadata)

    @overload
    def APILoginAliyundriveRefreshtoken(
        self, 
        arg: dict | clouddrive.pb2.LoginAliyundriveRefreshtokenRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginAliyundriveRefreshtoken(
        self, 
        arg: dict | clouddrive.pb2.LoginAliyundriveRefreshtokenRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginAliyundriveRefreshtoken(
        self, 
        arg: dict | clouddrive.pb2.LoginAliyundriveRefreshtokenRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add AliyunDrive with refresh token

        ------------------- protobuf rpc definition --------------------

        // add AliyunDrive with refresh token
        rpc APILoginAliyundriveRefreshtoken(LoginAliyundriveRefreshtokenRequest)
            returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginAliyundriveRefreshtokenRequest {
          string refreshToken = 1;
          bool useOpenAPI = 2;
        }
        """
        arg = to_message(clouddrive.pb2.LoginAliyundriveRefreshtokenRequest, arg)
        if async_:
            return self.async_stub.APILoginAliyundriveRefreshtoken(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginAliyundriveRefreshtoken(arg, metadata=self.metadata)

    @overload
    def APILoginAliyunDriveQRCode(
        self, 
        arg: dict | clouddrive.pb2.LoginAliyundriveQRCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.QRCodeScanMessage]:
        ...
    @overload
    def APILoginAliyunDriveQRCode(
        self, 
        arg: dict | clouddrive.pb2.LoginAliyundriveQRCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.QRCodeScanMessage]]:
        ...
    def APILoginAliyunDriveQRCode(
        self, 
        arg: dict | clouddrive.pb2.LoginAliyundriveQRCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.QRCodeScanMessage] | Coroutine[Any, Any, Iterable[clouddrive.pb2.QRCodeScanMessage]]:
        """
        add AliyunDrive with qr scanning

        ------------------- protobuf rpc definition --------------------

        // add AliyunDrive with qr scanning
        rpc APILoginAliyunDriveQRCode(LoginAliyundriveQRCodeRequest)
            returns (stream QRCodeScanMessage) {}

        ------------------- protobuf type definition -------------------

        message LoginAliyundriveQRCodeRequest {
          bool useOpenAPI = 1;
          optional ProxyInfo apiProxy = 2;
          optional ProxyInfo dataProxy = 3;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        message QRCodeScanMessage {
          QRCodeScanMessageType messageType = 1;
          string message = 2;
        }
        enum QRCodeScanMessageType {
          SHOW_IMAGE = 0;
          SHOW_IMAGE_CONTENT = 1;
          CHANGE_STATUS = 2;
          CLOSE = 3;
          ERROR = 4;
        }
        """
        arg = to_message(clouddrive.pb2.LoginAliyundriveQRCodeRequest, arg)
        if async_:
            return self.async_stub.APILoginAliyunDriveQRCode(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginAliyunDriveQRCode(arg, metadata=self.metadata)

    @overload
    def APILoginBaiduPanOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginBaiduPanOAuthRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginBaiduPanOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginBaiduPanOAuthRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginBaiduPanOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginBaiduPanOAuthRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add BaiduPan with OAuth result

        ------------------- protobuf rpc definition --------------------

        // add BaiduPan with OAuth result
        rpc APILoginBaiduPanOAuth(LoginBaiduPanOAuthRequest)
            returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginBaiduPanOAuthRequest {
          string refresh_token = 1;
          string access_token = 2;
          uint64 expires_in = 3;
          optional ProxyInfo apiProxy = 4;
          optional ProxyInfo dataProxy = 5;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginBaiduPanOAuthRequest, arg)
        if async_:
            return self.async_stub.APILoginBaiduPanOAuth(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginBaiduPanOAuth(arg, metadata=self.metadata)

    @overload
    def APILoginOneDriveOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginOneDriveOAuthRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginOneDriveOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginOneDriveOAuthRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginOneDriveOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginOneDriveOAuthRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add OneDrive with OAuth result

        ------------------- protobuf rpc definition --------------------

        // add OneDrive with OAuth result
        rpc APILoginOneDriveOAuth(LoginOneDriveOAuthRequest)
            returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginOneDriveOAuthRequest {
          string refresh_token = 1;
          string access_token = 2;
          uint64 expires_in = 3;
          optional ProxyInfo apiProxy = 4;
          optional ProxyInfo dataProxy = 5;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginOneDriveOAuthRequest, arg)
        if async_:
            return self.async_stub.APILoginOneDriveOAuth(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginOneDriveOAuth(arg, metadata=self.metadata)

    @overload
    def ApiLoginGoogleDriveOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginGoogleDriveOAuthRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def ApiLoginGoogleDriveOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginGoogleDriveOAuthRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def ApiLoginGoogleDriveOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginGoogleDriveOAuthRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add Google Drive with OAuth result

        ------------------- protobuf rpc definition --------------------

        // add Google Drive with OAuth result
        rpc ApiLoginGoogleDriveOAuth(LoginGoogleDriveOAuthRequest)
            returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginGoogleDriveOAuthRequest {
          string refresh_token = 1;
          string access_token = 2;
          uint64 expires_in = 3;
          optional ProxyInfo apiProxy = 4;
          optional ProxyInfo dataProxy = 5;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginGoogleDriveOAuthRequest, arg)
        if async_:
            return self.async_stub.ApiLoginGoogleDriveOAuth(arg, metadata=self.metadata)
        else:
            return self.stub.ApiLoginGoogleDriveOAuth(arg, metadata=self.metadata)

    @overload
    def ApiLoginGoogleDriveRefreshToken(
        self, 
        arg: dict | clouddrive.pb2.LoginGoogleDriveRefreshTokenRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def ApiLoginGoogleDriveRefreshToken(
        self, 
        arg: dict | clouddrive.pb2.LoginGoogleDriveRefreshTokenRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def ApiLoginGoogleDriveRefreshToken(
        self, 
        arg: dict | clouddrive.pb2.LoginGoogleDriveRefreshTokenRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add Google Drive with refresh token

        ------------------- protobuf rpc definition --------------------

        // add Google Drive with refresh token
        rpc ApiLoginGoogleDriveRefreshToken(LoginGoogleDriveRefreshTokenRequest)
            returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginGoogleDriveRefreshTokenRequest {
          string client_id = 1;
          string client_secret = 2;
          string refresh_token = 3;
          optional ProxyInfo apiProxy = 4;
          optional ProxyInfo dataProxy = 5;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginGoogleDriveRefreshTokenRequest, arg)
        if async_:
            return self.async_stub.ApiLoginGoogleDriveRefreshToken(arg, metadata=self.metadata)
        else:
            return self.stub.ApiLoginGoogleDriveRefreshToken(arg, metadata=self.metadata)

    @overload
    def ApiLoginXunleiOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginXunleiOAuthRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def ApiLoginXunleiOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginXunleiOAuthRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def ApiLoginXunleiOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginXunleiOAuthRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add Xunlei Drive with OAuth result

        ------------------- protobuf rpc definition --------------------

        // add Xunlei Drive with OAuth result
        rpc ApiLoginXunleiOAuth(LoginXunleiOAuthRequest) returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginXunleiOAuthRequest {
          string refresh_token = 1;
          string access_token = 2;
          uint64 expires_in = 3;
          optional ProxyInfo apiProxy = 4;
          optional ProxyInfo dataProxy = 5;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginXunleiOAuthRequest, arg)
        if async_:
            return self.async_stub.ApiLoginXunleiOAuth(arg, metadata=self.metadata)
        else:
            return self.stub.ApiLoginXunleiOAuth(arg, metadata=self.metadata)

    @overload
    def ApiLoginXunleiOpenOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginXunleiOpenOAuthRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def ApiLoginXunleiOpenOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginXunleiOpenOAuthRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def ApiLoginXunleiOpenOAuth(
        self, 
        arg: dict | clouddrive.pb2.LoginXunleiOpenOAuthRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add XunleiOpen with OAuth result

        ------------------- protobuf rpc definition --------------------

        // add XunleiOpen with OAuth result
        rpc ApiLoginXunleiOpenOAuth(LoginXunleiOpenOAuthRequest)
            returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginXunleiOpenOAuthRequest {
          string refresh_token = 1;
          string access_token = 2;
          uint64 expires_in = 3;
          optional ProxyInfo apiProxy = 4;
          optional ProxyInfo dataProxy = 5;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginXunleiOpenOAuthRequest, arg)
        if async_:
            return self.async_stub.ApiLoginXunleiOpenOAuth(arg, metadata=self.metadata)
        else:
            return self.stub.ApiLoginXunleiOpenOAuth(arg, metadata=self.metadata)

    @overload
    def ApiLogin123panOAuth(
        self, 
        arg: dict | clouddrive.pb2.Login123panOAuthRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def ApiLogin123panOAuth(
        self, 
        arg: dict | clouddrive.pb2.Login123panOAuthRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def ApiLogin123panOAuth(
        self, 
        arg: dict | clouddrive.pb2.Login123panOAuthRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add 123 cloud with client id and client secret

        ------------------- protobuf rpc definition --------------------

        // add 123 cloud with client id and client secret
        rpc ApiLogin123panOAuth(Login123panOAuthRequest) returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message Login123panOAuthRequest {
          string refresh_token = 1;
          string access_token = 2;
          uint64 expires_in = 3;
          optional ProxyInfo apiProxy = 4;
          optional ProxyInfo dataProxy = 5;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.Login123panOAuthRequest, arg)
        if async_:
            return self.async_stub.ApiLogin123panOAuth(arg, metadata=self.metadata)
        else:
            return self.stub.ApiLogin123panOAuth(arg, metadata=self.metadata)

    @overload
    def CreateOAuthState(
        self, 
        arg: dict | clouddrive.pb2.CreateOAuthStateRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CreateOAuthStateResult:
        ...
    @overload
    def CreateOAuthState(
        self, 
        arg: dict | clouddrive.pb2.CreateOAuthStateRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CreateOAuthStateResult]:
        ...
    def CreateOAuthState(
        self, 
        arg: dict | clouddrive.pb2.CreateOAuthStateRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CreateOAuthStateResult | Coroutine[Any, Any, clouddrive.pb2.CreateOAuthStateResult]:
        """
        mint a short-lived signed OAuth `state` token (relayed to cloudfs server).
        The frontend uses the returned token as the OAuth `state` parameter; the
        oauth callback server validates it before processing the redirect callback.

        ------------------- protobuf rpc definition --------------------

        // mint a short-lived signed OAuth `state` token (relayed to cloudfs server).
        // The frontend uses the returned token as the OAuth `state` parameter; the
        // oauth callback server validates it before processing the redirect callback.
        rpc CreateOAuthState(CreateOAuthStateRequest) returns (CreateOAuthStateResult) {}

        ------------------- protobuf type definition -------------------

        message CreateOAuthStateRequest {
          string oauth_type = 1; // provider key, e.g. \"google_drive\", \"onedrive\"
          string return_url = 2; // where tokens are delivered after the callback
          optional string device_id = 3; // carried through the flow for xunlei
          // PKCE code_verifier, sealed into the signed state for guangyapan so the
          // oauth_callback server can complete the token exchange (PKCE has no secret).
          optional string code_verifier = 4;
        }
        message CreateOAuthStateResult {
          bool success = 1;
          string error_message = 2;
          string state = 3; // signed token to use as the OAuth `state` parameter
          uint64 expires_in = 4; // token lifetime in seconds
        }
        """
        arg = to_message(clouddrive.pb2.CreateOAuthStateRequest, arg)
        if async_:
            return self.async_stub.CreateOAuthState(arg, metadata=self.metadata)
        else:
            return self.stub.CreateOAuthState(arg, metadata=self.metadata)

    @overload
    def APILogin189QRCode(
        self, 
        arg: dict | clouddrive.pb2.Login189QRCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.QRCodeScanMessage]:
        ...
    @overload
    def APILogin189QRCode(
        self, 
        arg: dict | clouddrive.pb2.Login189QRCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.QRCodeScanMessage]]:
        ...
    def APILogin189QRCode(
        self, 
        arg: dict | clouddrive.pb2.Login189QRCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.QRCodeScanMessage] | Coroutine[Any, Any, Iterable[clouddrive.pb2.QRCodeScanMessage]]:
        """
        add 189 cloud with qr scanning

        ------------------- protobuf rpc definition --------------------

        // add 189 cloud with qr scanning
        rpc APILogin189QRCode(Login189QRCodeRequest)
            returns (stream QRCodeScanMessage) {}

        ------------------- protobuf type definition -------------------

        message Login189QRCodeRequest {
          optional ProxyInfo apiProxy = 1;
          optional ProxyInfo dataProxy = 2;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        message QRCodeScanMessage {
          QRCodeScanMessageType messageType = 1;
          string message = 2;
        }
        enum QRCodeScanMessageType {
          SHOW_IMAGE = 0;
          SHOW_IMAGE_CONTENT = 1;
          CHANGE_STATUS = 2;
          CLOSE = 3;
          ERROR = 4;
        }
        """
        arg = to_message(clouddrive.pb2.Login189QRCodeRequest, arg)
        if async_:
            return self.async_stub.APILogin189QRCode(arg, metadata=self.metadata)
        else:
            return self.stub.APILogin189QRCode(arg, metadata=self.metadata)

    @overload
    def APILoginWebDav(
        self, 
        arg: dict | clouddrive.pb2.LoginWebDavRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginWebDav(
        self, 
        arg: dict | clouddrive.pb2.LoginWebDavRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginWebDav(
        self, 
        arg: dict | clouddrive.pb2.LoginWebDavRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add PikPak cloud with username and password
        rpc APILoginPikPak(UserLoginRequest) returns (APILoginResult) {}
        add webdav

        ------------------- protobuf rpc definition --------------------

        // add PikPak cloud with username and password
        // rpc APILoginPikPak(UserLoginRequest) returns (APILoginResult) {}
        // add webdav
        rpc APILoginWebDav(LoginWebDavRequest) returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginWebDavRequest {
          string serverUrl = 1;
          string userName = 2;
          string password = 3;
          bool doNotSyncToCloud = 4; // If true, do NOT sync this API config to cloud (default: false, meaning sync by default)
          optional ProxyInfo apiProxy = 5; // Optional API proxy for the initial connection and metadata calls
          optional ProxyInfo dataProxy = 6; // Optional data proxy for file upload/download
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginWebDavRequest, arg)
        if async_:
            return self.async_stub.APILoginWebDav(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginWebDav(arg, metadata=self.metadata)

    @overload
    def APILoginS3(
        self, 
        arg: dict | clouddrive.pb2.LoginS3Request, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginS3(
        self, 
        arg: dict | clouddrive.pb2.LoginS3Request, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginS3(
        self, 
        arg: dict | clouddrive.pb2.LoginS3Request, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add Amazon S3 or S3-compatible storage

        ------------------- protobuf rpc definition --------------------

        // add Amazon S3 or S3-compatible storage
        rpc APILoginS3(LoginS3Request) returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginS3Request {
          string accessKeyId = 1; // AWS Access Key ID
          string secretAccessKey = 2; // AWS Secret Access Key
          string region = 3; // AWS region (e.g., \"us-east-1\")
          string bucket = 4; // S3 bucket name
          optional string endpoint = 5; // Custom endpoint URL for S3-compatible services (e.g., MinIO, Wasabi)
          bool pathStyle = 6; // Use path-style URLs instead of virtual-hosted style (required for some S3-compatible services)
          bool doNotSyncToCloud = 7; // If true, do NOT sync this API config to cloud (default: false, meaning sync by default)
          optional uint32 signatureVersion = 8; // S3 signature version: 2 or 4 (default 4)
          optional ProxyInfo apiProxy = 9; // Optional API proxy for the initial connection and metadata calls
          optional ProxyInfo dataProxy = 10; // Optional data proxy for file upload/download
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginS3Request, arg)
        if async_:
            return self.async_stub.APILoginS3(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginS3(arg, metadata=self.metadata)

    @overload
    def APIAddLocalFolder(
        self, 
        arg: dict | clouddrive.pb2.AddLocalFolderRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APIAddLocalFolder(
        self, 
        arg: dict | clouddrive.pb2.AddLocalFolderRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APIAddLocalFolder(
        self, 
        arg: dict | clouddrive.pb2.AddLocalFolderRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add local folder

        ------------------- protobuf rpc definition --------------------

        // add local folder
        rpc APIAddLocalFolder(AddLocalFolderRequest) returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message AddLocalFolderRequest { string localFolderPath = 1; }
        """
        arg = to_message(clouddrive.pb2.AddLocalFolderRequest, arg)
        if async_:
            return self.async_stub.APIAddLocalFolder(arg, metadata=self.metadata)
        else:
            return self.stub.APIAddLocalFolder(arg, metadata=self.metadata)

    @overload
    def APILoginCloudDrive(
        self, 
        arg: dict | clouddrive.pb2.LoginCloudDriveRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginCloudDrive(
        self, 
        arg: dict | clouddrive.pb2.LoginCloudDriveRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginCloudDrive(
        self, 
        arg: dict | clouddrive.pb2.LoginCloudDriveRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add remote clouddrive

        ------------------- protobuf rpc definition --------------------

        // add remote clouddrive
        rpc APILoginCloudDrive(LoginCloudDriveRequest) returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginCloudDriveRequest {
          string grpcUrl = 1;
          string token = 2;
          // If true, connect with TLS certificate/hostname validation disabled (for
          // self-signed certs)
          bool insecureTls = 3;
          bool doNotSyncToCloud = 4; // If true, do NOT sync this API config to cloud (default: false, meaning sync by default)
          optional ProxyInfo apiProxy = 5;
          optional ProxyInfo dataProxy = 6;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginCloudDriveRequest, arg)
        if async_:
            return self.async_stub.APILoginCloudDrive(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginCloudDrive(arg, metadata=self.metadata)

    @overload
    def APILoginSftp(
        self, 
        arg: dict | clouddrive.pb2.LoginSftpRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginSftp(
        self, 
        arg: dict | clouddrive.pb2.LoginSftpRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginSftp(
        self, 
        arg: dict | clouddrive.pb2.LoginSftpRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add SFTP server

        ------------------- protobuf rpc definition --------------------

        // add SFTP server
        rpc APILoginSftp(LoginSftpRequest) returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginSftpRequest {
          string host = 1;
          uint32 port = 2; // default 22
          string userName = 3;
          string password = 4; // password authentication
          optional string privateKey = 5;     // PEM-encoded private key for key-based auth
          optional string passphrase = 6;     // passphrase for encrypted private keys
          optional string rootPath = 7;       // remote root directory (default: \"/\")
          bool doNotSyncToCloud = 8;
          optional ProxyInfo apiProxy = 9;
          optional ProxyInfo dataProxy = 10;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginSftpRequest, arg)
        if async_:
            return self.async_stub.APILoginSftp(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginSftp(arg, metadata=self.metadata)

    @overload
    def APILoginFtp(
        self, 
        arg: dict | clouddrive.pb2.LoginFtpRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginFtp(
        self, 
        arg: dict | clouddrive.pb2.LoginFtpRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginFtp(
        self, 
        arg: dict | clouddrive.pb2.LoginFtpRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add FTP/FTPS server

        ------------------- protobuf rpc definition --------------------

        // add FTP/FTPS server
        rpc APILoginFtp(LoginFtpRequest) returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginFtpRequest {
          string host = 1;
          uint32 port = 2; // default 21
          string userName = 3;
          string password = 4;
          bool useTls = 5; // enable FTPS (TLS)
          optional string rootPath = 6;       // remote root directory (default: \"/\")
          bool doNotSyncToCloud = 7;
          optional ProxyInfo apiProxy = 8;
          optional ProxyInfo dataProxy = 9;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginFtpRequest, arg)
        if async_:
            return self.async_stub.APILoginFtp(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginFtp(arg, metadata=self.metadata)

    @overload
    def APILoginSmb(
        self, 
        arg: dict | clouddrive.pb2.LoginSmbRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.APILoginResult:
        ...
    @overload
    def APILoginSmb(
        self, 
        arg: dict | clouddrive.pb2.LoginSmbRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        ...
    def APILoginSmb(
        self, 
        arg: dict | clouddrive.pb2.LoginSmbRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.APILoginResult | Coroutine[Any, Any, clouddrive.pb2.APILoginResult]:
        """
        add SMB/CIFS share

        ------------------- protobuf rpc definition --------------------

        // add SMB/CIFS share
        rpc APILoginSmb(LoginSmbRequest) returns (APILoginResult) {}

        ------------------- protobuf type definition -------------------

        message APILoginResult {
          bool success = 1;
          string errorMessage = 2;
        }
        message LoginSmbRequest {
          string server = 1; // SMB server hostname or IP
          string share = 2; // share name (e.g., \"SharedDocs\")
          uint32 port = 3; // default 445
          string userName = 4;
          string password = 5;
          optional string workgroup = 6;      // domain/workgroup
          optional string rootPath = 7;       // path within share (default: \"/\")
          bool doNotSyncToCloud = 8;
          optional ProxyInfo apiProxy = 9;
          optional ProxyInfo dataProxy = 10;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.LoginSmbRequest, arg)
        if async_:
            return self.async_stub.APILoginSmb(arg, metadata=self.metadata)
        else:
            return self.stub.APILoginSmb(arg, metadata=self.metadata)

    @overload
    def DiscoverSmbServers(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.DiscoverSmbServersResult:
        ...
    @overload
    def DiscoverSmbServers(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.DiscoverSmbServersResult]:
        ...
    def DiscoverSmbServers(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.DiscoverSmbServersResult | Coroutine[Any, Any, clouddrive.pb2.DiscoverSmbServersResult]:
        """
        discover SMB servers on the local network

        ------------------- protobuf rpc definition --------------------

        // discover SMB servers on the local network
        rpc DiscoverSmbServers(google.protobuf.Empty) returns (DiscoverSmbServersResult) {}

        ------------------- protobuf type definition -------------------

        message DiscoverSmbServersResult {
          repeated SmbServerInfo servers = 1;
        }
        message SmbServerInfo {
          string name = 1; // server name (e.g., \"MINIPC-Y10\")
          string address = 2; // IP address or hostname
        }
        """
        if async_:
            return self.async_stub.DiscoverSmbServers(Empty(), metadata=self.metadata)
        else:
            return self.stub.DiscoverSmbServers(Empty(), metadata=self.metadata)

    @overload
    def DiscoverSmbShares(
        self, 
        arg: dict | clouddrive.pb2.DiscoverSmbSharesRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.DiscoverSmbSharesResult:
        ...
    @overload
    def DiscoverSmbShares(
        self, 
        arg: dict | clouddrive.pb2.DiscoverSmbSharesRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.DiscoverSmbSharesResult]:
        ...
    def DiscoverSmbShares(
        self, 
        arg: dict | clouddrive.pb2.DiscoverSmbSharesRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.DiscoverSmbSharesResult | Coroutine[Any, Any, clouddrive.pb2.DiscoverSmbSharesResult]:
        """
        discover SMB shares on a server

        ------------------- protobuf rpc definition --------------------

        // discover SMB shares on a server
        rpc DiscoverSmbShares(DiscoverSmbSharesRequest) returns (DiscoverSmbSharesResult) {}

        ------------------- protobuf type definition -------------------

        message DiscoverSmbSharesRequest {
          string server = 1;
          uint32 port = 2; // default 445
          string userName = 3;
          string password = 4;
          optional string workgroup = 5;
        }
        message DiscoverSmbSharesResult {
          repeated string shareNames = 1;
        }
        """
        arg = to_message(clouddrive.pb2.DiscoverSmbSharesRequest, arg)
        if async_:
            return self.async_stub.DiscoverSmbShares(arg, metadata=self.metadata)
        else:
            return self.stub.DiscoverSmbShares(arg, metadata=self.metadata)

    @overload
    def RemoveCloudAPI(
        self, 
        arg: dict | clouddrive.pb2.RemoveCloudAPIRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def RemoveCloudAPI(
        self, 
        arg: dict | clouddrive.pb2.RemoveCloudAPIRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def RemoveCloudAPI(
        self, 
        arg: dict | clouddrive.pb2.RemoveCloudAPIRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        remove a cloud

        ------------------- protobuf rpc definition --------------------

        // remove a cloud
        rpc RemoveCloudAPI(RemoveCloudAPIRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        message RemoveCloudAPIRequest {
          string cloudName = 1;
          string userName = 2;
          bool permanentRemove = 3;
        }
        """
        arg = to_message(clouddrive.pb2.RemoveCloudAPIRequest, arg)
        if async_:
            return self.async_stub.RemoveCloudAPI(arg, metadata=self.metadata)
        else:
            return self.stub.RemoveCloudAPI(arg, metadata=self.metadata)

    @overload
    def GetAllCloudApis(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CloudAPIList:
        ...
    @overload
    def GetAllCloudApis(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CloudAPIList]:
        ...
    def GetAllCloudApis(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CloudAPIList | Coroutine[Any, Any, clouddrive.pb2.CloudAPIList]:
        """
        get all cloud apis

        ------------------- protobuf rpc definition --------------------

        // get all cloud apis
        rpc GetAllCloudApis(google.protobuf.Empty) returns (CloudAPIList) {}

        ------------------- protobuf type definition -------------------

        message CloudAPI {
          string name = 1;
          string userName = 2;
          string nickName = 3;
          bool isLocked = 4; // isLocked means the cloudAPI is set to can't open files,
          // due to user's membership issue
          bool supportMultiThreadUploading = 5;
          bool supportQpsLimit = 6;
          bool isCloudEventListenerRunning = 7;
          bool hasPromotions = 8; // if true, this cloud has promotions
          optional string promotionTitle =
              9;                     // promotion title, if hasPromotions is true
          optional string path = 10; // the path of the cloud
          bool supportHttpDownload = 11; // whether this cloud provider supports HTTP (non-HTTPS) downloads
          bool readOnly = 12; // true when this cloud is read-only (all write ops unsupported)
        }
        message CloudAPIList { repeated CloudAPI apis = 1; }
        """
        if async_:
            return self.async_stub.GetAllCloudApis(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetAllCloudApis(Empty(), metadata=self.metadata)

    @overload
    def GetCloudAPIConfig(
        self, 
        arg: dict | clouddrive.pb2.GetCloudAPIConfigRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CloudAPIConfig:
        ...
    @overload
    def GetCloudAPIConfig(
        self, 
        arg: dict | clouddrive.pb2.GetCloudAPIConfigRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CloudAPIConfig]:
        ...
    def GetCloudAPIConfig(
        self, 
        arg: dict | clouddrive.pb2.GetCloudAPIConfigRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CloudAPIConfig | Coroutine[Any, Any, clouddrive.pb2.CloudAPIConfig]:
        """
        get CloudAPI configuration

        ------------------- protobuf rpc definition --------------------

        // get CloudAPI configuration
        rpc GetCloudAPIConfig(GetCloudAPIConfigRequest) returns (CloudAPIConfig) {}

        ------------------- protobuf type definition -------------------

        message CloudAPIConfig {
          uint32 maxDownloadThreads = 1;
          uint64 minReadLengthKB = 2;
          uint64 maxReadLengthKB = 3;
          uint64 defaultReadLengthKB = 4;
          uint64 maxBufferPoolSizeMB = 5;
          double maxQueriesPerSecond = 6;
          bool forceIpv4 = 7;
          optional ProxyInfo apiProxy = 8;
          optional ProxyInfo dataProxy = 9;
          optional string customUserAgent = 10;
          optional uint32 maxUploadThreads = 11;
          // for CloudDrive API only: whether to use insecure TLS when connecting
          optional bool insecureTls = 12;
          // whether to use HTTP instead of HTTPS for downloads to save CPU (disabled by default)
          optional bool useHttpDownload = 13;
          // whether to request direct URLs when available (requires enable_direct_link user role)
          optional bool supportDirectLink = 14;
          // whether this cloud API supports direct download URLs (read-only, determined by API implementation)
          optional bool supportDirectDownloadUrl = 15;
          // field 16 and 17 removed: disk cache settings moved to per-folder (SetFolderDiskCache)
          reserved 16, 17;
          // Read-only caps reported by the server so clients can bound user input.
          // Each is the effective per-cloud (and platform-clamped, where applicable)
          // upper bound. Absent / zero means \"no advertised cap; client should fall
          // back to a sensible default\". Ignored on SetCloudAPIConfig.
          optional uint32 maxDownloadThreadsLimit = 18;
          optional uint64 maxBufferPoolSizeMBLimit = 19;
          optional double maxQueriesPerSecondLimit = 20;
          // For files from this cloud, copy/upload tasks read the source bytes via the
          // legacy multi-thread buffered downloader (ENTRY_READER_MANAGER) instead of
          // the single long HTTP GET stream. Useful when single-stream throughput is
          // lower than the destination write/upload speed. Applies to both hash
          // preprocessing and upload byte streaming.
          optional bool useMultithreadDownloaderForCopy = 21;
        }
        message GetCloudAPIConfigRequest {
          string cloudName = 1;
          string userName = 2;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        """
        arg = to_message(clouddrive.pb2.GetCloudAPIConfigRequest, arg)
        if async_:
            return self.async_stub.GetCloudAPIConfig(arg, metadata=self.metadata)
        else:
            return self.stub.GetCloudAPIConfig(arg, metadata=self.metadata)

    @overload
    def SetCloudAPIConfig(
        self, 
        arg: dict | clouddrive.pb2.SetCloudAPIConfigRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SetCloudAPIConfig(
        self, 
        arg: dict | clouddrive.pb2.SetCloudAPIConfigRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SetCloudAPIConfig(
        self, 
        arg: dict | clouddrive.pb2.SetCloudAPIConfigRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        set CloudAPI configuration

        ------------------- protobuf rpc definition --------------------

        // set CloudAPI configuration
        rpc SetCloudAPIConfig(SetCloudAPIConfigRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message CloudAPIConfig {
          uint32 maxDownloadThreads = 1;
          uint64 minReadLengthKB = 2;
          uint64 maxReadLengthKB = 3;
          uint64 defaultReadLengthKB = 4;
          uint64 maxBufferPoolSizeMB = 5;
          double maxQueriesPerSecond = 6;
          bool forceIpv4 = 7;
          optional ProxyInfo apiProxy = 8;
          optional ProxyInfo dataProxy = 9;
          optional string customUserAgent = 10;
          optional uint32 maxUploadThreads = 11;
          // for CloudDrive API only: whether to use insecure TLS when connecting
          optional bool insecureTls = 12;
          // whether to use HTTP instead of HTTPS for downloads to save CPU (disabled by default)
          optional bool useHttpDownload = 13;
          // whether to request direct URLs when available (requires enable_direct_link user role)
          optional bool supportDirectLink = 14;
          // whether this cloud API supports direct download URLs (read-only, determined by API implementation)
          optional bool supportDirectDownloadUrl = 15;
          // field 16 and 17 removed: disk cache settings moved to per-folder (SetFolderDiskCache)
          reserved 16, 17;
          // Read-only caps reported by the server so clients can bound user input.
          // Each is the effective per-cloud (and platform-clamped, where applicable)
          // upper bound. Absent / zero means \"no advertised cap; client should fall
          // back to a sensible default\". Ignored on SetCloudAPIConfig.
          optional uint32 maxDownloadThreadsLimit = 18;
          optional uint64 maxBufferPoolSizeMBLimit = 19;
          optional double maxQueriesPerSecondLimit = 20;
          // For files from this cloud, copy/upload tasks read the source bytes via the
          // legacy multi-thread buffered downloader (ENTRY_READER_MANAGER) instead of
          // the single long HTTP GET stream. Useful when single-stream throughput is
          // lower than the destination write/upload speed. Applies to both hash
          // preprocessing and upload byte streaming.
          optional bool useMultithreadDownloaderForCopy = 21;
        }
        message SetCloudAPIConfigRequest {
          string cloudName = 1;
          string userName = 2;
          CloudAPIConfig config = 3;
        }
        """
        if async_:
            async def request():
                await self.async_stub.SetCloudAPIConfig(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SetCloudAPIConfig(arg, metadata=self.metadata)
            return None

    @overload
    def GetSystemSettings(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.SystemSettings:
        ...
    @overload
    def GetSystemSettings(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.SystemSettings]:
        ...
    def GetSystemSettings(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.SystemSettings | Coroutine[Any, Any, clouddrive.pb2.SystemSettings]:
        """
        get all system setings value

        ------------------- protobuf rpc definition --------------------

        // get all system setings value
        rpc GetSystemSettings(google.protobuf.Empty) returns (SystemSettings) {}

        ------------------- protobuf type definition -------------------

        enum LogLevel {
          Trace = 0;
          Debug = 1;
          Info = 2;
          Warn = 3;
          Error = 4;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        message StringList { repeated string values = 1; }
        message SystemSettings {
          // 0 means never expire, will live forever
          optional uint64 dirCacheTimeToLiveSecs = 1;
          optional uint64 maxPreProcessTasks = 2;
          optional uint64 maxProcessTasks = 3;
          optional string tempFileLocation = 4;
          optional bool syncWithCloud = 5;
          // time in secs to clear download task when no read operation
          optional uint64 readDownloaderTimeoutSecs = 6;
          // time in secs to wait before upload a local temp file
          optional uint64 uploadDelaySecs = 7;
          optional StringList processBlackList = 8;
          optional StringList uploadIgnoredExtensions = 9;
          optional UpdateChannel updateChannel = 10;
          optional double maxDownloadSpeedKBytesPerSecond = 11;
          optional double maxUploadSpeedKBytesPerSecond = 12;
          optional string deviceName = 13;
          optional bool dirCachePersistence = 14;
          optional string dirCacheDbLocation = 15;
          optional LogLevel fileLogLevel = 16;
          optional LogLevel terminalLogLevel = 17;
          optional LogLevel backupLogLevel = 18;
          optional bool EnableAutoRegisterDevice = 19;
          optional LogLevel realtimeLogLevel = 20;
          // Operator priority order for upload scheduling. Use [\"Natural\"] or empty to
          // disable priority, default is [\"Mount\", \"Backup\", \"CopyTask\"]
          optional StringList operatorPriorityOrder = 21;
          // Standalone proxy settings for downloading update packages
          optional ProxyInfo updateProxy = 22;
          // Delay in seconds before starting process (default: 0)
          optional uint64 startDelaySecs = 23;

          // Root directory for storing cached segments
          optional string fileBufferDiskCacheLocation = 24;
          // Max bytes allowed for disk cache; LRU eviction keeps size under this
          optional uint64 fileBufferDiskCacheMaxBytes = 25;
          // Proxy settings for reaching CloudFS account server (cloudfs.zhenyunpan.com)
          optional ProxyInfo cloudfsProxy = 26;
          // Log file rotation settings.
          // All 4 fields must be sent together in SetSystemSettings; when any
          // field is present the server updates all 4, so omitted size fields
          // are interpreted as \"no limit\" rather than \"don't change\".
          //
          // Max size in bytes for a single log file before rotation:
          //   not set (None) = no limit (file grows indefinitely)
          //   0              = disable logging to file
          //   > 0            = rotate when the file exceeds this size
          optional uint64 maxFileLogSizeBytes = 27;
          optional uint64 maxBackupLogSizeBytes = 28;
          // Max number of rotated log files to keep (default: 10)
          optional uint32 maxFileLogFiles = 29;
          optional uint32 maxBackupLogFiles = 30;

          // Backup full-scan resource bounds (issue #462).
          // These 3 fields form a group: when maxConcurrentBackupWalkers is present in
          // SetSystemSettings the server rewrites all 3, so an omitted water mark means
          // \"no limit\" rather than \"don't change\". Omit all 3 to leave them unchanged.
          //
          // High/low water marks bound the in-memory transfer queue while a backup scan
          // enqueues tasks (the walker pauses adding at high, resumes at low):
          //   not set (None) = no limit (unbounded, legacy behavior)
          //   > 0            = bound the pending-task queue to this size
          optional uint64 backupQueueHighWater = 31;
          optional uint64 backupQueueLowWater = 32;
          // Max backup scans (source walkers) running concurrently (default 1, min 1).
          // Extra due scans queue until a slot frees.
          optional uint32 maxConcurrentBackupWalkers = 33;

          // When copying files across cloud storages, spool the source file to a local
          // temp file during hash calculation so the upload stage doesn't download the
          // source a second time. Falls back to double download when local temp space
          // is insufficient. Default: false.
          optional bool useTempFileForCrossCloudCopy = 34;
        }
        enum UpdateChannel {
          Release = 0;
          Beta = 1;
        }
        """
        if async_:
            return self.async_stub.GetSystemSettings(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetSystemSettings(Empty(), metadata=self.metadata)

    @overload
    def SetSystemSettings(
        self, 
        arg: dict | clouddrive.pb2.SystemSettings, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SetSystemSettings(
        self, 
        arg: dict | clouddrive.pb2.SystemSettings, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SetSystemSettings(
        self, 
        arg: dict | clouddrive.pb2.SystemSettings, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        set selected system settings value

        ------------------- protobuf rpc definition --------------------

        // set selected system settings value
        rpc SetSystemSettings(SystemSettings) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        enum LogLevel {
          Trace = 0;
          Debug = 1;
          Info = 2;
          Warn = 3;
          Error = 4;
        }
        message ProxyInfo {
          ProxyType proxyType = 1;
          string host = 2;
          uint32 port = 3;
          optional string username = 4;
          optional string password = 5;
        }
        message StringList { repeated string values = 1; }
        message SystemSettings {
          // 0 means never expire, will live forever
          optional uint64 dirCacheTimeToLiveSecs = 1;
          optional uint64 maxPreProcessTasks = 2;
          optional uint64 maxProcessTasks = 3;
          optional string tempFileLocation = 4;
          optional bool syncWithCloud = 5;
          // time in secs to clear download task when no read operation
          optional uint64 readDownloaderTimeoutSecs = 6;
          // time in secs to wait before upload a local temp file
          optional uint64 uploadDelaySecs = 7;
          optional StringList processBlackList = 8;
          optional StringList uploadIgnoredExtensions = 9;
          optional UpdateChannel updateChannel = 10;
          optional double maxDownloadSpeedKBytesPerSecond = 11;
          optional double maxUploadSpeedKBytesPerSecond = 12;
          optional string deviceName = 13;
          optional bool dirCachePersistence = 14;
          optional string dirCacheDbLocation = 15;
          optional LogLevel fileLogLevel = 16;
          optional LogLevel terminalLogLevel = 17;
          optional LogLevel backupLogLevel = 18;
          optional bool EnableAutoRegisterDevice = 19;
          optional LogLevel realtimeLogLevel = 20;
          // Operator priority order for upload scheduling. Use [\"Natural\"] or empty to
          // disable priority, default is [\"Mount\", \"Backup\", \"CopyTask\"]
          optional StringList operatorPriorityOrder = 21;
          // Standalone proxy settings for downloading update packages
          optional ProxyInfo updateProxy = 22;
          // Delay in seconds before starting process (default: 0)
          optional uint64 startDelaySecs = 23;

          // Root directory for storing cached segments
          optional string fileBufferDiskCacheLocation = 24;
          // Max bytes allowed for disk cache; LRU eviction keeps size under this
          optional uint64 fileBufferDiskCacheMaxBytes = 25;
          // Proxy settings for reaching CloudFS account server (cloudfs.zhenyunpan.com)
          optional ProxyInfo cloudfsProxy = 26;
          // Log file rotation settings.
          // All 4 fields must be sent together in SetSystemSettings; when any
          // field is present the server updates all 4, so omitted size fields
          // are interpreted as \"no limit\" rather than \"don't change\".
          //
          // Max size in bytes for a single log file before rotation:
          //   not set (None) = no limit (file grows indefinitely)
          //   0              = disable logging to file
          //   > 0            = rotate when the file exceeds this size
          optional uint64 maxFileLogSizeBytes = 27;
          optional uint64 maxBackupLogSizeBytes = 28;
          // Max number of rotated log files to keep (default: 10)
          optional uint32 maxFileLogFiles = 29;
          optional uint32 maxBackupLogFiles = 30;

          // Backup full-scan resource bounds (issue #462).
          // These 3 fields form a group: when maxConcurrentBackupWalkers is present in
          // SetSystemSettings the server rewrites all 3, so an omitted water mark means
          // \"no limit\" rather than \"don't change\". Omit all 3 to leave them unchanged.
          //
          // High/low water marks bound the in-memory transfer queue while a backup scan
          // enqueues tasks (the walker pauses adding at high, resumes at low):
          //   not set (None) = no limit (unbounded, legacy behavior)
          //   > 0            = bound the pending-task queue to this size
          optional uint64 backupQueueHighWater = 31;
          optional uint64 backupQueueLowWater = 32;
          // Max backup scans (source walkers) running concurrently (default 1, min 1).
          // Extra due scans queue until a slot frees.
          optional uint32 maxConcurrentBackupWalkers = 33;

          // When copying files across cloud storages, spool the source file to a local
          // temp file during hash calculation so the upload stage doesn't download the
          // source a second time. Falls back to double download when local temp space
          // is insufficient. Default: false.
          optional bool useTempFileForCrossCloudCopy = 34;
        }
        enum UpdateChannel {
          Release = 0;
          Beta = 1;
        }
        """
        if async_:
            async def request():
                await self.async_stub.SetSystemSettings(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SetSystemSettings(arg, metadata=self.metadata)
            return None

    @overload
    def SetDirCacheTimeSecs(
        self, 
        arg: dict | clouddrive.pb2.SetDirCacheTimeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SetDirCacheTimeSecs(
        self, 
        arg: dict | clouddrive.pb2.SetDirCacheTimeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SetDirCacheTimeSecs(
        self, 
        arg: dict | clouddrive.pb2.SetDirCacheTimeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        set dir cache time

        ------------------- protobuf rpc definition --------------------

        // set dir cache time
        rpc SetDirCacheTimeSecs(SetDirCacheTimeRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message SetDirCacheTimeRequest {
          string path = 1;
          // if not present, please delete the value to restore default
          optional uint64 dirCachTimeToLiveSecs = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.SetDirCacheTimeSecs(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SetDirCacheTimeSecs(arg, metadata=self.metadata)
            return None

    @overload
    def GetEffectiveDirCacheTimeSecs(
        self, 
        arg: dict | clouddrive.pb2.GetEffectiveDirCacheTimeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetEffectiveDirCacheTimeResult:
        ...
    @overload
    def GetEffectiveDirCacheTimeSecs(
        self, 
        arg: dict | clouddrive.pb2.GetEffectiveDirCacheTimeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetEffectiveDirCacheTimeResult]:
        ...
    def GetEffectiveDirCacheTimeSecs(
        self, 
        arg: dict | clouddrive.pb2.GetEffectiveDirCacheTimeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetEffectiveDirCacheTimeResult | Coroutine[Any, Any, clouddrive.pb2.GetEffectiveDirCacheTimeResult]:
        """
        get dir cache time in effect (default value will be returned)

        ------------------- protobuf rpc definition --------------------

        // get dir cache time in effect (default value will be returned)
        rpc GetEffectiveDirCacheTimeSecs(GetEffectiveDirCacheTimeRequest)
            returns (GetEffectiveDirCacheTimeResult) {}

        ------------------- protobuf type definition -------------------

        message GetEffectiveDirCacheTimeRequest { string path = 1; }
        message GetEffectiveDirCacheTimeResult { uint64 dirCacheTimeSecs = 1; }
        """
        arg = to_message(clouddrive.pb2.GetEffectiveDirCacheTimeRequest, arg)
        if async_:
            return self.async_stub.GetEffectiveDirCacheTimeSecs(arg, metadata=self.metadata)
        else:
            return self.stub.GetEffectiveDirCacheTimeSecs(arg, metadata=self.metadata)

    @overload
    def ForceExpireDirCache(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ForceExpireDirCache(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ForceExpireDirCache(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        force expire dir cache recursively

        ------------------- protobuf rpc definition --------------------

        // force expire dir cache recursively
        rpc ForceExpireDirCache(FileRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        if async_:
            async def request():
                await self.async_stub.ForceExpireDirCache(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ForceExpireDirCache(arg, metadata=self.metadata)
            return None

    @overload
    def VacuumDirCache(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def VacuumDirCache(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def VacuumDirCache(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        vacuum persisted dir cache database (requires persistence enabled)

        ------------------- protobuf rpc definition --------------------

        // vacuum persisted dir cache database (requires persistence enabled)
        rpc VacuumDirCache(google.protobuf.Empty) returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.VacuumDirCache(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.VacuumDirCache(Empty(), metadata=self.metadata)
            return None

    @overload
    def GetVacuumProgress(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.VacuumProgressResult:
        ...
    @overload
    def GetVacuumProgress(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.VacuumProgressResult]:
        ...
    def GetVacuumProgress(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.VacuumProgressResult | Coroutine[Any, Any, clouddrive.pb2.VacuumProgressResult]:
        """
        get vacuum progress status

        ------------------- protobuf rpc definition --------------------

        // get vacuum progress status
        rpc GetVacuumProgress(google.protobuf.Empty) returns (VacuumProgressResult) {}

        ------------------- protobuf type definition -------------------

        message VacuumProgressResult {
          VacuumStatus status = 1;
          optional google.protobuf.Timestamp startTime = 2;
          optional google.protobuf.Timestamp endTime = 3;
          uint64 sizeBefore = 4; // Database size before vacuum
          uint64 sizeAfter = 5; // Database size after vacuum (only set when completed)
          optional string errorMessage = 6; // Error message if failed
        }
        enum VacuumStatus {
          VACUUM_IDLE = 0;
          VACUUM_RUNNING = 1;
          VACUUM_COMPLETED = 2;
          VACUUM_FAILED = 3;
        }
        """
        if async_:
            return self.async_stub.GetVacuumProgress(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetVacuumProgress(Empty(), metadata=self.metadata)

    @overload
    def GetDirCacheDbSize(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetDirCacheDbSizeResult:
        ...
    @overload
    def GetDirCacheDbSize(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetDirCacheDbSizeResult]:
        ...
    def GetDirCacheDbSize(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetDirCacheDbSizeResult | Coroutine[Any, Any, clouddrive.pb2.GetDirCacheDbSizeResult]:
        """
        get dir cache database file size in bytes (includes WAL and SHM files)

        ------------------- protobuf rpc definition --------------------

        // get dir cache database file size in bytes (includes WAL and SHM files)
        rpc GetDirCacheDbSize(google.protobuf.Empty)
            returns (GetDirCacheDbSizeResult) {}

        ------------------- protobuf type definition -------------------

        message GetDirCacheDbSizeResult {
          uint64 totalSizeBytes = 1; // Total size including main db + WAL + SHM files
          bool isVacuuming = 2; // Whether database is currently being vacuumed
        }
        """
        if async_:
            return self.async_stub.GetDirCacheDbSize(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetDirCacheDbSize(Empty(), metadata=self.metadata)

    @overload
    def GetOpenFileTable(
        self, 
        arg: dict | clouddrive.pb2.GetOpenFileTableRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.OpenFileTable:
        ...
    @overload
    def GetOpenFileTable(
        self, 
        arg: dict | clouddrive.pb2.GetOpenFileTableRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.OpenFileTable]:
        ...
    def GetOpenFileTable(
        self, 
        arg: dict | clouddrive.pb2.GetOpenFileTableRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.OpenFileTable | Coroutine[Any, Any, clouddrive.pb2.OpenFileTable]:
        """
        get open file table
        deprecated, use GetOpenFileHandles instead

        ------------------- protobuf rpc definition --------------------

        // get open file table
        // deprecated, use GetOpenFileHandles instead
        rpc GetOpenFileTable(GetOpenFileTableRequest) returns (OpenFileTable) {}

        ------------------- protobuf type definition -------------------

        message GetOpenFileTableRequest { bool includeDir = 1; }
        message OpenFileTable {
          map<uint64, string> openFileTable = 1;
          uint64 localOpenFileCount = 2;
        }
        """
        arg = to_message(clouddrive.pb2.GetOpenFileTableRequest, arg)
        if async_:
            return self.async_stub.GetOpenFileTable(arg, metadata=self.metadata)
        else:
            return self.stub.GetOpenFileTable(arg, metadata=self.metadata)

    @overload
    def GetDirCacheTable(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.DirCacheTable:
        ...
    @overload
    def GetDirCacheTable(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.DirCacheTable]:
        ...
    def GetDirCacheTable(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.DirCacheTable | Coroutine[Any, Any, clouddrive.pb2.DirCacheTable]:
        """
        get dir cache table

        ------------------- protobuf rpc definition --------------------

        // get dir cache table
        rpc GetDirCacheTable(google.protobuf.Empty) returns (DirCacheTable) {}

        ------------------- protobuf type definition -------------------

        message DirCacheTable { map<string, DirCacheItem> dirCacheTable = 1; }
        """
        if async_:
            return self.async_stub.GetDirCacheTable(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetDirCacheTable(Empty(), metadata=self.metadata)

    @overload
    def GetReferencedEntryPaths(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.StringList:
        ...
    @overload
    def GetReferencedEntryPaths(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.StringList]:
        ...
    def GetReferencedEntryPaths(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.StringList | Coroutine[Any, Any, clouddrive.pb2.StringList]:
        """
        get referenced entry paths of parent path

        ------------------- protobuf rpc definition --------------------

        // get referenced entry paths of parent path
        rpc GetReferencedEntryPaths(FileRequest) returns (StringList) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        message StringList { repeated string values = 1; }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.GetReferencedEntryPaths(arg, metadata=self.metadata)
        else:
            return self.stub.GetReferencedEntryPaths(arg, metadata=self.metadata)

    @overload
    def GetTempFileTable(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.TempFileTable:
        ...
    @overload
    def GetTempFileTable(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.TempFileTable]:
        ...
    def GetTempFileTable(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.TempFileTable | Coroutine[Any, Any, clouddrive.pb2.TempFileTable]:
        """
        get temp file table

        ------------------- protobuf rpc definition --------------------

        // get temp file table
        rpc GetTempFileTable(google.protobuf.Empty) returns (TempFileTable) {}

        ------------------- protobuf type definition -------------------

        message TempFileTable {
          uint64 count = 1;
          repeated string tempFiles = 2;
        }
        """
        if async_:
            return self.async_stub.GetTempFileTable(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetTempFileTable(Empty(), metadata=self.metadata)

    @overload
    def PushTaskChange(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.GetAllTasksCountResult]:
        ...
    @overload
    def PushTaskChange(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.GetAllTasksCountResult]]:
        ...
    def PushTaskChange(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.GetAllTasksCountResult] | Coroutine[Any, Any, Iterable[clouddrive.pb2.GetAllTasksCountResult]]:
        """
        [deprecated] use PushMessage instead
        push upload/download task count changes to client, also can be used for
        client to detect conenction broken

        ------------------- protobuf rpc definition --------------------

        // [deprecated] use PushMessage instead
        // push upload/download task count changes to client, also can be used for
        // client to detect conenction broken
        rpc PushTaskChange(google.protobuf.Empty)
            returns (stream GetAllTasksCountResult) {}

        ------------------- protobuf type definition -------------------

        message GetAllTasksCountResult {
          uint32 downloadCount = 1;
          uint32 uploadCount = 2;
          uint32 copyTaskCount = 6;
          PushMessage pushMessage = 3;
          bool hasUpdate = 4;
          repeated UploadFileInfo uploadFileStatusChanges =
              5; // upload file status changed
        }
        message PushMessage { string clouddriveVersion = 1; }
        message UploadFileInfo {
          enum Status {
            WaitforPreprocessing = 0;
            Preprocessing = 1;
            Cancelled = 2;
            Transfer = 3;
            Pause = 4;
            Finish = 5;
            Skipped = 6;
            Inqueue = 7;
            Ignored = 8;
            Error = 9;
            FatalError = 10;
          }
          enum OperatorType {
            Mount = 0; // Mount means the file is being uploaded by mounted file system
                       // operations
            Copy = 1; // Copy means the file is being uploaded by a copy task
            BackupFile = 2; // BackupFile means the file is being
                              // uploaded by a backup task
            RemoteUpload = 3; // RemoteUpload means the file is being uploaded by a
                              // remote upload task
          }
          string key = 1;
          string destPath = 2;
          uint64 size = 3;
          uint64 transferedBytes = 4;
          string status = 5;
          string errorMessage = 6;
          OperatorType operatorType = 7;
          Status statusEnum = 8;
        }
        """
        if async_:
            return self.async_stub.PushTaskChange(Empty(), metadata=self.metadata)
        else:
            return self.stub.PushTaskChange(Empty(), metadata=self.metadata)

    @overload
    def PushMessage(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.CloudDrivePushMessage]:
        ...
    @overload
    def PushMessage(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.CloudDrivePushMessage]]:
        ...
    def PushMessage(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.CloudDrivePushMessage] | Coroutine[Any, Any, Iterable[clouddrive.pb2.CloudDrivePushMessage]]:
        """
        general message notification

        ------------------- protobuf rpc definition --------------------

        // general message notification
        rpc PushMessage(google.protobuf.Empty)
            returns (stream CloudDrivePushMessage) {}

        ------------------- protobuf type definition -------------------

        message CloudDrivePushMessage {
          enum MessageType {
            DOWNLOADER_COUNT = 0;
            UPLOADER_COUNT = 1;
            UPDATE_STATUS = 2;
            FORCE_EXIT = 3;
            FILE_SYSTEM_CHANGE = 4;
            MOUNT_POINT_CHANGE = 5;
            COPY_TASK_COUNT = 6;
            LOG_MESSAGE = 7;
            MERGE_TASKS = 8;
          }
          MessageType messageType = 1;
          oneof data {
            TransferTaskStatus transferTaskStatus = 2;
            UpdateStatus updateStatus = 3;
            ExitedMessage exitedMessage = 4;
            FileSystemChange fileSystemChange = 5;
            MountPointChange mountPointChange = 6;
            LogMessage logMessage = 7;
            MergeTaskUpdate mergeTaskUpdate = 8;
          }
        }
        message ExitedMessage {
          enum ExitReason {
            UNKNOWN = 0;
            KICKEDOUT_BY_USER = 1;
            KICKEDOUT_BY_SERVER = 2;
            PASSWORD_CHANGED = 3;
            RESTART = 4;
            SHUTDOWN = 5;
          }
          ExitReason exitReason = 1;
          string message = 2;
        }
        message FileSystemChange {
          enum ChangeType {
            CREATE = 0;
            DELETE = 1;
            RENAME = 2;
          }
          ChangeType changeType = 1;
          bool isDirectory = 2;
          string path = 3;
          // only used for RENAME type
          optional string newPath = 4;
          // not available for DELETE type
          optional CloudDriveFile theFile = 5;
        }
        message LogMessage {
          enum LogLevel {
            TRACE = 0;
            DEBUG = 1;
            INFO = 2;
            WARN = 3;
            ERROR = 4;
          }
          LogLevel level = 1;
          string message = 2;
          string target = 3; // the module/target where the log originated
          google.protobuf.Timestamp timestamp = 4;
          map<string, string> fields = 6; // additional fields from the log record
        }
        // Realtime update for merge tasks (folder recursive merges)
        message MergeTaskUpdate {
          repeated MergeTask mergeTasks = 1;
          // optional: when a single file is merged, include the file path(s)
          optional string lastMergedPath = 2;    // source file path
          optional string lastMergedNewPath = 3; // destination file path
        }
        message MountPointChange {
          enum ActionType {
            MOUNT = 0;
            UNMOUNT = 1;
          }
          ActionType actionType = 1;
          string mountPoint = 2;
          bool success = 3;
          string failReason = 4;
        }
        message UpdateStatus {
          enum UpdatePhase {
            NO_UPDATE = 0;
            DOWNLOADING = 1;
            READY_TO_UPDATE = 2;
            UPDATING = 3;
            UPDATE_SUCCESS = 4;
            UPDATE_FAILED = 5;
          }
          UpdatePhase updatePhase = 1;
          optional string newVersion = 2;
          optional string message = 3;
          string clouddriveVersion = 4;
          optional uint64 downloadedBytes =
              5; // only available when updatePhase is DOWNLOADING
          optional uint64 totalBytes =
              6; // only available when updatePhase is DOWNLOADING
        }
        """
        if async_:
            return self.async_stub.PushMessage(Empty(), metadata=self.metadata)
        else:
            return self.stub.PushMessage(Empty(), metadata=self.metadata)

    @overload
    def GetCloudDrive1UserData(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.StringResult:
        ...
    @overload
    def GetCloudDrive1UserData(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.StringResult]:
        ...
    def GetCloudDrive1UserData(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.StringResult | Coroutine[Any, Any, clouddrive.pb2.StringResult]:
        """
        get CloudDrive1's user data string

        ------------------- protobuf rpc definition --------------------

        // get CloudDrive1's user data string
        rpc GetCloudDrive1UserData(google.protobuf.Empty) returns (StringResult) {}

        ------------------- protobuf type definition -------------------

        message StringResult { string result = 1; }
        """
        if async_:
            return self.async_stub.GetCloudDrive1UserData(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetCloudDrive1UserData(Empty(), metadata=self.metadata)

    @overload
    def GetServiceCapabilities(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.ServiceCapabilities:
        ...
    @overload
    def GetServiceCapabilities(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.ServiceCapabilities]:
        ...
    def GetServiceCapabilities(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.ServiceCapabilities | Coroutine[Any, Any, clouddrive.pb2.ServiceCapabilities]:
        """
        get service capabilities (restart/update availability)

        ------------------- protobuf rpc definition --------------------

        // get service capabilities (restart/update availability)
        rpc GetServiceCapabilities(google.protobuf.Empty) returns (ServiceCapabilities) {}

        ------------------- protobuf type definition -------------------

        message ServiceCapabilities {
          bool canRestart = 1; // whether service restart is available
          bool canUpdate = 2; // whether service update is available
        }
        """
        if async_:
            return self.async_stub.GetServiceCapabilities(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetServiceCapabilities(Empty(), metadata=self.metadata)

    @overload
    def RestartService(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RestartService(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RestartService(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        restart service

        ------------------- protobuf rpc definition --------------------

        // restart service
        rpc RestartService(google.protobuf.Empty) returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.RestartService(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RestartService(Empty(), metadata=self.metadata)
            return None

    @overload
    def ShutdownService(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ShutdownService(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ShutdownService(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        shutdown service

        ------------------- protobuf rpc definition --------------------

        // shutdown service
        rpc ShutdownService(google.protobuf.Empty) returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.ShutdownService(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ShutdownService(Empty(), metadata=self.metadata)
            return None

    @overload
    def HasUpdate(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.UpdateResult:
        ...
    @overload
    def HasUpdate(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.UpdateResult]:
        ...
    def HasUpdate(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.UpdateResult | Coroutine[Any, Any, clouddrive.pb2.UpdateResult]:
        """
        check if has updates available

        ------------------- protobuf rpc definition --------------------

        // check if has updates available
        rpc HasUpdate(google.protobuf.Empty) returns (UpdateResult) {}

        ------------------- protobuf type definition -------------------

        message UpdateResult {
          bool hasUpdate = 1;
          string newVersion = 2;
          string description = 3;
        }
        """
        if async_:
            return self.async_stub.HasUpdate(Empty(), metadata=self.metadata)
        else:
            return self.stub.HasUpdate(Empty(), metadata=self.metadata)

    @overload
    def CheckUpdate(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.UpdateResult:
        ...
    @overload
    def CheckUpdate(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.UpdateResult]:
        ...
    def CheckUpdate(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.UpdateResult | Coroutine[Any, Any, clouddrive.pb2.UpdateResult]:
        """
        check software updates

        ------------------- protobuf rpc definition --------------------

        // check software updates
        rpc CheckUpdate(google.protobuf.Empty) returns (UpdateResult) {}

        ------------------- protobuf type definition -------------------

        message UpdateResult {
          bool hasUpdate = 1;
          string newVersion = 2;
          string description = 3;
        }
        """
        if async_:
            return self.async_stub.CheckUpdate(Empty(), metadata=self.metadata)
        else:
            return self.stub.CheckUpdate(Empty(), metadata=self.metadata)

    @overload
    def DownloadUpdate(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def DownloadUpdate(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def DownloadUpdate(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        download newest version

        ------------------- protobuf rpc definition --------------------

        // download newest version
        rpc DownloadUpdate(google.protobuf.Empty) returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.DownloadUpdate(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.DownloadUpdate(Empty(), metadata=self.metadata)
            return None

    @overload
    def UpdateSystem(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def UpdateSystem(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def UpdateSystem(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        update to newest version

        ------------------- protobuf rpc definition --------------------

        // update to newest version
        rpc UpdateSystem(google.protobuf.Empty) returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.UpdateSystem(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.UpdateSystem(Empty(), metadata=self.metadata)
            return None

    @overload
    def TestUpdate(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def TestUpdate(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def TestUpdate(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        test update process

        ------------------- protobuf rpc definition --------------------

        // test update process
        rpc TestUpdate(FileRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        if async_:
            async def request():
                await self.async_stub.TestUpdate(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.TestUpdate(arg, metadata=self.metadata)
            return None

    @overload
    def GetMetaData(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileMetaData:
        ...
    @overload
    def GetMetaData(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileMetaData]:
        ...
    def GetMetaData(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileMetaData | Coroutine[Any, Any, clouddrive.pb2.FileMetaData]:
        """
        get file metadata

        ------------------- protobuf rpc definition --------------------

        // get file metadata
        rpc GetMetaData(FileRequest) returns (FileMetaData) {}

        ------------------- protobuf type definition -------------------

        message FileMetaData { map<string, string> metadata = 1; }
        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.GetMetaData(arg, metadata=self.metadata)
        else:
            return self.stub.GetMetaData(arg, metadata=self.metadata)

    @overload
    def GetOriginalPath(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.StringResult:
        ...
    @overload
    def GetOriginalPath(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.StringResult]:
        ...
    def GetOriginalPath(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.StringResult | Coroutine[Any, Any, clouddrive.pb2.StringResult]:
        """
        get file's original path from search result

        ------------------- protobuf rpc definition --------------------

        // get file's original path from search result
        rpc GetOriginalPath(FileRequest) returns (StringResult) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        message StringResult { string result = 1; }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.GetOriginalPath(arg, metadata=self.metadata)
        else:
            return self.stub.GetOriginalPath(arg, metadata=self.metadata)

    @overload
    def ChangePassword(
        self, 
        arg: dict | clouddrive.pb2.ChangePasswordRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def ChangePassword(
        self, 
        arg: dict | clouddrive.pb2.ChangePasswordRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def ChangePassword(
        self, 
        arg: dict | clouddrive.pb2.ChangePasswordRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        change password

        ------------------- protobuf rpc definition --------------------

        // change password
        rpc ChangePassword(ChangePasswordRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message ChangePasswordRequest {
          string oldPassword = 1;
          string newPassword = 2;
          optional string totpCode = 3;
        }
        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        """
        arg = to_message(clouddrive.pb2.ChangePasswordRequest, arg)
        if async_:
            return self.async_stub.ChangePassword(arg, metadata=self.metadata)
        else:
            return self.stub.ChangePassword(arg, metadata=self.metadata)

    @overload
    def CreateFile(
        self, 
        arg: dict | clouddrive.pb2.CreateFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CreateFileResult:
        ...
    @overload
    def CreateFile(
        self, 
        arg: dict | clouddrive.pb2.CreateFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CreateFileResult]:
        ...
    def CreateFile(
        self, 
        arg: dict | clouddrive.pb2.CreateFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CreateFileResult | Coroutine[Any, Any, clouddrive.pb2.CreateFileResult]:
        """
        create a new file

        ------------------- protobuf rpc definition --------------------

        // create a new file
        rpc CreateFile(CreateFileRequest) returns (CreateFileResult) {}

        ------------------- protobuf type definition -------------------

        message CreateFileRequest {
          string parentPath = 1;
          string fileName = 2;
        }
        message CreateFileResult { uint64 fileHandle = 1; }
        """
        arg = to_message(clouddrive.pb2.CreateFileRequest, arg)
        if async_:
            return self.async_stub.CreateFile(arg, metadata=self.metadata)
        else:
            return self.stub.CreateFile(arg, metadata=self.metadata)

    @overload
    def CloseFile(
        self, 
        arg: dict | clouddrive.pb2.CloseFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def CloseFile(
        self, 
        arg: dict | clouddrive.pb2.CloseFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def CloseFile(
        self, 
        arg: dict | clouddrive.pb2.CloseFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        close an opened file

        ------------------- protobuf rpc definition --------------------

        // close an opened file
        rpc CloseFile(CloseFileRequest) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message CloseFileRequest { uint64 fileHandle = 1; }
        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        """
        arg = to_message(clouddrive.pb2.CloseFileRequest, arg)
        if async_:
            return self.async_stub.CloseFile(arg, metadata=self.metadata)
        else:
            return self.stub.CloseFile(arg, metadata=self.metadata)

    @overload
    def WriteToFileStream(
        self, 
        arg: Sequence[dict | clouddrive.pb2.WriteFileRequest], 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.WriteFileResult:
        ...
    @overload
    def WriteToFileStream(
        self, 
        arg: Sequence[dict | clouddrive.pb2.WriteFileRequest], 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.WriteFileResult]:
        ...
    def WriteToFileStream(
        self, 
        arg: Sequence[dict | clouddrive.pb2.WriteFileRequest], 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.WriteFileResult | Coroutine[Any, Any, clouddrive.pb2.WriteFileResult]:
        """
        write a stream to an opened file

        ------------------- protobuf rpc definition --------------------

        // write a stream to an opened file
        rpc WriteToFileStream(stream WriteFileRequest) returns (WriteFileResult) {}

        ------------------- protobuf type definition -------------------

        message WriteFileRequest {
          uint64 fileHandle = 1;
          uint64 startPos = 2;
          uint64 length = 3;
          bytes buffer = 4;
          bool closeFile = 5;
        }
        message WriteFileResult { uint64 bytesWritten = 1; }
        """
        arg = [to_message(clouddrive.pb2.WriteFileRequest, a) for a in arg]
        if async_:
            return self.async_stub.WriteToFileStream(arg, metadata=self.metadata)
        else:
            return self.stub.WriteToFileStream(arg, metadata=self.metadata)

    @overload
    def WriteToFile(
        self, 
        arg: dict | clouddrive.pb2.WriteFileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.WriteFileResult:
        ...
    @overload
    def WriteToFile(
        self, 
        arg: dict | clouddrive.pb2.WriteFileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.WriteFileResult]:
        ...
    def WriteToFile(
        self, 
        arg: dict | clouddrive.pb2.WriteFileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.WriteFileResult | Coroutine[Any, Any, clouddrive.pb2.WriteFileResult]:
        """
        write to an opened file

        ------------------- protobuf rpc definition --------------------

        // write to an opened file
        rpc WriteToFile(WriteFileRequest) returns (WriteFileResult) {}

        ------------------- protobuf type definition -------------------

        message WriteFileRequest {
          uint64 fileHandle = 1;
          uint64 startPos = 2;
          uint64 length = 3;
          bytes buffer = 4;
          bool closeFile = 5;
        }
        message WriteFileResult { uint64 bytesWritten = 1; }
        """
        arg = to_message(clouddrive.pb2.WriteFileRequest, arg)
        if async_:
            return self.async_stub.WriteToFile(arg, metadata=self.metadata)
        else:
            return self.stub.WriteToFile(arg, metadata=self.metadata)

    @overload
    def GetPromotions(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetPromotionsResult:
        ...
    @overload
    def GetPromotions(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetPromotionsResult]:
        ...
    def GetPromotions(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetPromotionsResult | Coroutine[Any, Any, clouddrive.pb2.GetPromotionsResult]:
        """
        get promotions

        ------------------- protobuf rpc definition --------------------

        // get promotions
        rpc GetPromotions(google.protobuf.Empty) returns (GetPromotionsResult) {}

        ------------------- protobuf type definition -------------------

        message GetPromotionsResult { repeated Promotion promotions = 1; }
        message Promotion {
          string id = 1;
          string cloudName = 2;
          string title = 3;
          optional string subTitle = 4;
          string rules = 5;
          optional string notice = 6;
          string url = 7;
        }
        """
        if async_:
            return self.async_stub.GetPromotions(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetPromotions(Empty(), metadata=self.metadata)

    @overload
    def GetPromotionsByCloud(
        self, 
        arg: dict | clouddrive.pb2.CloudAPIRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetPromotionsResult:
        ...
    @overload
    def GetPromotionsByCloud(
        self, 
        arg: dict | clouddrive.pb2.CloudAPIRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetPromotionsResult]:
        ...
    def GetPromotionsByCloud(
        self, 
        arg: dict | clouddrive.pb2.CloudAPIRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetPromotionsResult | Coroutine[Any, Any, clouddrive.pb2.GetPromotionsResult]:
        """
        get promotions of a specific cloud, cloud_name is the name of the cloud

        ------------------- protobuf rpc definition --------------------

        // get promotions of a specific cloud, cloud_name is the name of the cloud
        rpc GetPromotionsByCloud(CloudAPIRequest) returns (GetPromotionsResult) {}

        ------------------- protobuf type definition -------------------

        message CloudAPIRequest {
          string cloudName = 1;
          optional string userName = 2; // unused, but kept for compatibility
        }
        message GetPromotionsResult { repeated Promotion promotions = 1; }
        message Promotion {
          string id = 1;
          string cloudName = 2;
          string title = 3;
          optional string subTitle = 4;
          string rules = 5;
          optional string notice = 6;
          string url = 7;
        }
        """
        arg = to_message(clouddrive.pb2.CloudAPIRequest, arg)
        if async_:
            return self.async_stub.GetPromotionsByCloud(arg, metadata=self.metadata)
        else:
            return self.stub.GetPromotionsByCloud(arg, metadata=self.metadata)

    @overload
    def UpdatePromotionResult(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def UpdatePromotionResult(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def UpdatePromotionResult(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        update promotion result after purchased

        ------------------- protobuf rpc definition --------------------

        // update promotion result after purchased
        rpc UpdatePromotionResult(google.protobuf.Empty)
            returns (google.protobuf.Empty) {}
        """
        if async_:
            async def request():
                await self.async_stub.UpdatePromotionResult(Empty(), metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.UpdatePromotionResult(Empty(), metadata=self.metadata)
            return None

    @overload
    def UpdatePromotionResultByCloud(
        self, 
        arg: dict | clouddrive.pb2.UpdatePromotionResultByCloudRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def UpdatePromotionResultByCloud(
        self, 
        arg: dict | clouddrive.pb2.UpdatePromotionResultByCloudRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def UpdatePromotionResultByCloud(
        self, 
        arg: dict | clouddrive.pb2.UpdatePromotionResultByCloudRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        update promotion result after purchased with cloud name

        ------------------- protobuf rpc definition --------------------

        // update promotion result after purchased with cloud name
        rpc UpdatePromotionResultByCloud(UpdatePromotionResultByCloudRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message UpdatePromotionResultByCloudRequest {
          string cloudName = 1;
          optional string cloudAccountId = 2;
          optional string promotionId = 3;
        }
        """
        if async_:
            async def request():
                await self.async_stub.UpdatePromotionResultByCloud(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.UpdatePromotionResultByCloud(arg, metadata=self.metadata)
            return None

    @overload
    def SendPromotionAction(
        self, 
        arg: dict | clouddrive.pb2.SendPromotionActionRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SendPromotionAction(
        self, 
        arg: dict | clouddrive.pb2.SendPromotionActionRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SendPromotionAction(
        self, 
        arg: dict | clouddrive.pb2.SendPromotionActionRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        send promotion action when user has purchased a promotion

        ------------------- protobuf rpc definition --------------------

        // send promotion action when user has purchased a promotion
        rpc SendPromotionAction(SendPromotionActionRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message SendPromotionActionRequest {
          string cloudName = 1;
          optional string cloudAccountId = 2;
          optional string promotionId = 3;
        }
        """
        if async_:
            async def request():
                await self.async_stub.SendPromotionAction(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SendPromotionAction(arg, metadata=self.metadata)
            return None

    @overload
    def GetCloudDrivePlans(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.GetCloudDrivePlansResult:
        ...
    @overload
    def GetCloudDrivePlans(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.GetCloudDrivePlansResult]:
        ...
    def GetCloudDrivePlans(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.GetCloudDrivePlansResult | Coroutine[Any, Any, clouddrive.pb2.GetCloudDrivePlansResult]:
        """
        get cloudfs plans

        ------------------- protobuf rpc definition --------------------

        // get cloudfs plans
        rpc GetCloudDrivePlans(google.protobuf.Empty)
            returns (GetCloudDrivePlansResult) {}

        ------------------- protobuf type definition -------------------

        message CloudDrivePlan {
          string id = 1;
          string name = 2;
          string description = 3;
          double price = 4;
          optional int64 duration = 5;
          string durationDescription = 6;
          bool isActive = 7;
          optional string fontAwesomeIcon = 8;
          optional double originalPrice = 9;      // CNY
          repeated AccountRole planRoles = 10;
          optional double priceUsd = 11;          // predefined USD price (App Store price); unset if none
          optional double originalPriceUsd = 12;  // predefined USD original price; unset if none
          bool payableByBalance = 13;             // true if the user's CNY balance covers this plan (skip IAP)
          optional double balancePriceCny = 14;   // CNY deducted from balance if bought directly; unset if none
          string storeProductId = 15;             // the store SKU to buy for this plan (may be an upgrade SKU)
        }
        message GetCloudDrivePlansResult { repeated CloudDrivePlan plans = 1; }
        """
        if async_:
            return self.async_stub.GetCloudDrivePlans(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetCloudDrivePlans(Empty(), metadata=self.metadata)

    @overload
    def JoinPlan(
        self, 
        arg: dict | clouddrive.pb2.JoinPlanRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.JoinPlanResult:
        ...
    @overload
    def JoinPlan(
        self, 
        arg: dict | clouddrive.pb2.JoinPlanRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.JoinPlanResult]:
        ...
    def JoinPlan(
        self, 
        arg: dict | clouddrive.pb2.JoinPlanRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.JoinPlanResult | Coroutine[Any, Any, clouddrive.pb2.JoinPlanResult]:
        """
        join a plan

        ------------------- protobuf rpc definition --------------------

        // join a plan
        rpc JoinPlan(JoinPlanRequest) returns (JoinPlanResult) {}

        ------------------- protobuf type definition -------------------

        message JoinPlanRequest {
          string planId = 1;
          optional string couponCode = 2;
        }
        message JoinPlanResult {
          bool success = 1;
          double balance = 2;
          string planName = 3;
          string planDescription = 4;
          optional google.protobuf.Timestamp expireTime = 5;
          optional PaymentInfo paymentInfo = 6;
        }
        message PaymentInfo {
          string user_id = 1;
          string plan_id = 2;
          map<string, string> paymentMethods = 3;
          optional string coupon_code = 4;
          optional string machine_id = 5;
          optional string check_code = 6;
        }
        """
        arg = to_message(clouddrive.pb2.JoinPlanRequest, arg)
        if async_:
            return self.async_stub.JoinPlan(arg, metadata=self.metadata)
        else:
            return self.stub.JoinPlan(arg, metadata=self.metadata)

    @overload
    def BindCloudAccount(
        self, 
        arg: dict | clouddrive.pb2.BindCloudAccountRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def BindCloudAccount(
        self, 
        arg: dict | clouddrive.pb2.BindCloudAccountRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def BindCloudAccount(
        self, 
        arg: dict | clouddrive.pb2.BindCloudAccountRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        bind account to a cloud account id

        ------------------- protobuf rpc definition --------------------

        // bind account to a cloud account id
        rpc BindCloudAccount(BindCloudAccountRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message BindCloudAccountRequest {
          string cloudName = 1;
          string cloudAccountId = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.BindCloudAccount(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.BindCloudAccount(arg, metadata=self.metadata)
            return None

    @overload
    def TransferBalance(
        self, 
        arg: dict | clouddrive.pb2.TransferBalanceRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def TransferBalance(
        self, 
        arg: dict | clouddrive.pb2.TransferBalanceRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def TransferBalance(
        self, 
        arg: dict | clouddrive.pb2.TransferBalanceRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        transfer balance to another user

        ------------------- protobuf rpc definition --------------------

        // transfer balance to another user
        rpc TransferBalance(TransferBalanceRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message TransferBalanceRequest {
          string toUserName = 1;
          double amount = 2;
          string password = 3;
        }
        """
        if async_:
            async def request():
                await self.async_stub.TransferBalance(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.TransferBalance(arg, metadata=self.metadata)
            return None

    @overload
    def SendChangeEmailCode(
        self, 
        arg: dict | clouddrive.pb2.SendChangeEmailCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SendChangeEmailCode(
        self, 
        arg: dict | clouddrive.pb2.SendChangeEmailCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SendChangeEmailCode(
        self, 
        arg: dict | clouddrive.pb2.SendChangeEmailCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """

        ------------------- protobuf rpc definition --------------------

        rpc SendChangeEmailCode(SendChangeEmailCodeRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message SendChangeEmailCodeRequest {
          string newEmail = 1;
          string password = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.SendChangeEmailCode(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SendChangeEmailCode(arg, metadata=self.metadata)
            return None

    @overload
    def ChangeEmail(
        self, 
        arg: dict | clouddrive.pb2.ChangeEmailRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ChangeEmail(
        self, 
        arg: dict | clouddrive.pb2.ChangeEmailRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ChangeEmail(
        self, 
        arg: dict | clouddrive.pb2.ChangeEmailRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        change email

        ------------------- protobuf rpc definition --------------------

        // change email
        rpc ChangeEmail(ChangeEmailRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message ChangeEmailRequest {
          string newEmail = 1;
          string password = 2;
          optional string changeCode = 3;
          optional string totpCode = 4;
        }
        """
        if async_:
            async def request():
                await self.async_stub.ChangeEmail(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ChangeEmail(arg, metadata=self.metadata)
            return None

    @overload
    def ChangeEmailAndPassword(
        self, 
        arg: dict | clouddrive.pb2.ChangeEmailAndPasswordRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ChangeEmailAndPassword(
        self, 
        arg: dict | clouddrive.pb2.ChangeEmailAndPasswordRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ChangeEmailAndPassword(
        self, 
        arg: dict | clouddrive.pb2.ChangeEmailAndPasswordRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        change email and password, for trusted devices only

        ------------------- protobuf rpc definition --------------------

        // change email and password, for trusted devices only
        rpc ChangeEmailAndPassword(ChangeEmailAndPasswordRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message ChangeEmailAndPasswordRequest {
          string newEmail = 1;
          string newPassword = 2;
          bool syncUserDataWithCloud = 3;
        }
        """
        if async_:
            async def request():
                await self.async_stub.ChangeEmailAndPassword(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ChangeEmailAndPassword(arg, metadata=self.metadata)
            return None

    @overload
    def GetBalanceLog(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.BalanceLogResult:
        ...
    @overload
    def GetBalanceLog(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.BalanceLogResult]:
        ...
    def GetBalanceLog(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.BalanceLogResult | Coroutine[Any, Any, clouddrive.pb2.BalanceLogResult]:
        """
        chech balance log

        ------------------- protobuf rpc definition --------------------

        // chech balance log
        rpc GetBalanceLog(google.protobuf.Empty) returns (BalanceLogResult) {}

        ------------------- protobuf type definition -------------------

        message BalanceLog {
          double balance_before = 1;
          double balance_after = 2;
          double balance_change = 3;
          enum BalancceChangeOperation {
            Unknown = 0;
            Deposit = 1;
            Refund = 2;
          }
          BalancceChangeOperation operation = 4;
          string operation_source = 5;
          string operation_id = 6;
          google.protobuf.Timestamp operation_time = 7;
        }
        message BalanceLogResult { repeated BalanceLog logs = 1; }
        """
        if async_:
            return self.async_stub.GetBalanceLog(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetBalanceLog(Empty(), metadata=self.metadata)

    @overload
    def CheckActivationCode(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CheckActivationCodeResult:
        ...
    @overload
    def CheckActivationCode(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CheckActivationCodeResult]:
        ...
    def CheckActivationCode(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CheckActivationCodeResult | Coroutine[Any, Any, clouddrive.pb2.CheckActivationCodeResult]:
        """
        check activation code for a plan

        ------------------- protobuf rpc definition --------------------

        // check activation code for a plan
        rpc CheckActivationCode(StringValue) returns (CheckActivationCodeResult) {}

        ------------------- protobuf type definition -------------------

        message CheckActivationCodeResult {
          string planId = 1;
          string planName = 2;
          string planDescription = 3;
        }
        message StringValue { string value = 1; }
        """
        arg = to_message(clouddrive.pb2.StringValue, arg)
        if async_:
            return self.async_stub.CheckActivationCode(arg, metadata=self.metadata)
        else:
            return self.stub.CheckActivationCode(arg, metadata=self.metadata)

    @overload
    def ActivatePlan(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.JoinPlanResult:
        ...
    @overload
    def ActivatePlan(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.JoinPlanResult]:
        ...
    def ActivatePlan(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.JoinPlanResult | Coroutine[Any, Any, clouddrive.pb2.JoinPlanResult]:
        """
        Activate plan using an activation code

        ------------------- protobuf rpc definition --------------------

        // Activate plan using an activation code
        rpc ActivatePlan(StringValue) returns (JoinPlanResult) {}

        ------------------- protobuf type definition -------------------

        message JoinPlanResult {
          bool success = 1;
          double balance = 2;
          string planName = 3;
          string planDescription = 4;
          optional google.protobuf.Timestamp expireTime = 5;
          optional PaymentInfo paymentInfo = 6;
        }
        message PaymentInfo {
          string user_id = 1;
          string plan_id = 2;
          map<string, string> paymentMethods = 3;
          optional string coupon_code = 4;
          optional string machine_id = 5;
          optional string check_code = 6;
        }
        message StringValue { string value = 1; }
        """
        arg = to_message(clouddrive.pb2.StringValue, arg)
        if async_:
            return self.async_stub.ActivatePlan(arg, metadata=self.metadata)
        else:
            return self.stub.ActivatePlan(arg, metadata=self.metadata)

    @overload
    def CheckCouponCode(
        self, 
        arg: dict | clouddrive.pb2.CheckCouponCodeRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.CouponCodeResult:
        ...
    @overload
    def CheckCouponCode(
        self, 
        arg: dict | clouddrive.pb2.CheckCouponCodeRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.CouponCodeResult]:
        ...
    def CheckCouponCode(
        self, 
        arg: dict | clouddrive.pb2.CheckCouponCodeRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.CouponCodeResult | Coroutine[Any, Any, clouddrive.pb2.CouponCodeResult]:
        """
        check counpon code for a plan

        ------------------- protobuf rpc definition --------------------

        // check counpon code for a plan
        rpc CheckCouponCode(CheckCouponCodeRequest) returns (CouponCodeResult) {}

        ------------------- protobuf type definition -------------------

        message CheckCouponCodeRequest {
          string planId = 1;
          string couponCode = 2;
        }
        message CouponCodeResult {
          string couponCode = 1;
          string couponDescription = 2;
          bool isPercentage = 3;
          double couponDiscountAmount = 4;
        }
        """
        arg = to_message(clouddrive.pb2.CheckCouponCodeRequest, arg)
        if async_:
            return self.async_stub.CheckCouponCode(arg, metadata=self.metadata)
        else:
            return self.stub.CheckCouponCode(arg, metadata=self.metadata)

    @overload
    def GetStorePurchaseQuote(
        self, 
        arg: dict | clouddrive.pb2.GetStorePurchaseQuoteRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.StorePurchaseQuote:
        ...
    @overload
    def GetStorePurchaseQuote(
        self, 
        arg: dict | clouddrive.pb2.GetStorePurchaseQuoteRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.StorePurchaseQuote]:
        ...
    def GetStorePurchaseQuote(
        self, 
        arg: dict | clouddrive.pb2.GetStorePurchaseQuoteRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.StorePurchaseQuote | Coroutine[Any, Any, clouddrive.pb2.StorePurchaseQuote]:
        """
        IAP: quote the in-store price for a store product (server applies coupon/referral + CNY
        balance and returns the remainder to charge in-store)

        ------------------- protobuf rpc definition --------------------

        // IAP: quote the in-store price for a store product (server applies coupon/referral + CNY
        // balance and returns the remainder to charge in-store)
        rpc GetStorePurchaseQuote(GetStorePurchaseQuoteRequest)
            returns (StorePurchaseQuote) {}

        ------------------- protobuf type definition -------------------

        // IAP (App Store / Google Play / Meta Quest)
        message GetStorePurchaseQuoteRequest {
          string productId = 1;            // canonical product id, e.g. \"cd_app_pro\"
          optional string couponCode = 2;  // coupon or 8-char referral code
        }
        message StorePurchaseQuote {
          string productId = 1;
          string planId = 2;
          double basePriceUsd = 3;          // catalog/reference price
          double basePriceCny = 4;
          double couponDiscountCny = 5;
          double balanceAppliedCny = 6;     // CNY balance spent toward this purchase
          double finalPriceCny = 7;
          double finalPriceUsd = 8;         // charge THIS in-store (CNY remainder / 7, rounded up)
        }
        """
        arg = to_message(clouddrive.pb2.GetStorePurchaseQuoteRequest, arg)
        if async_:
            return self.async_stub.GetStorePurchaseQuote(arg, metadata=self.metadata)
        else:
            return self.stub.GetStorePurchaseQuote(arg, metadata=self.metadata)

    @overload
    def VerifyStorePurchase(
        self, 
        arg: dict | clouddrive.pb2.VerifyStorePurchaseRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.VerifyStorePurchaseResult:
        ...
    @overload
    def VerifyStorePurchase(
        self, 
        arg: dict | clouddrive.pb2.VerifyStorePurchaseRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.VerifyStorePurchaseResult]:
        ...
    def VerifyStorePurchase(
        self, 
        arg: dict | clouddrive.pb2.VerifyStorePurchaseRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.VerifyStorePurchaseResult | Coroutine[Any, Any, clouddrive.pb2.VerifyStorePurchaseResult]:
        """
        IAP: submit a store receipt for server validation + plan/entitlement activation

        ------------------- protobuf rpc definition --------------------

        // IAP: submit a store receipt for server validation + plan/entitlement activation
        rpc VerifyStorePurchase(VerifyStorePurchaseRequest)
            returns (VerifyStorePurchaseResult) {}

        ------------------- protobuf type definition -------------------

        message AccountStatusResult {
          string userName = 1;
          string emailConfirmed = 2;
          double accountBalance = 3;
          AccountPlan accountPlan = 4;
          repeated AccountRole accountRoles = 5;
          optional AccountPlan secondPlan = 6;
          optional string partnerReferralCode = 7;
          optional bool trustedDevice = 8; // if true, the device is trusted, no need to
          // provide password for changing email and password
          optional bool userNameIsDeviceId =
              9; // if true, the deviceId is used as userName, which can be changed to
          // a real user name later
          repeated BoundDevice boundDevices =
              10; // partner devices this account is bound to (empty if none); drives the unbind UI
          optional SubscriptionInfo subscription = 11; // present only for a store auto-renew subscription (Apple/Google/Meta); null for Alipay/one-time
        }
        message VerifyStorePurchaseRequest {
          string store = 1;                 // \"apple\" | \"google\" | \"meta\"
          string productId = 2;             // canonical product id
          string receipt = 3;               // Apple JWS / Google purchaseToken / Meta receipt
          optional string transactionId = 4;
          optional bool sandbox = 5;
          optional string couponCode = 6;   // same code used at quote time
          optional string packageName = 7;  // reserved for Google
        }
        message VerifyStorePurchaseResult {
          VerifyStorePurchaseStatus status = 1;
          optional AccountStatusResult accountStatus = 2; // fresh status on SUCCESS/ALREADY_ACTIVE
          optional string pendingReason = 3;              // set when status == PENDING
        }
        enum VerifyStorePurchaseStatus {
          VERIFY_STORE_PURCHASE_SUCCESS = 0;        // newly granted/extended
          VERIFY_STORE_PURCHASE_ALREADY_ACTIVE = 1; // idempotent re-submit / restore
          VERIFY_STORE_PURCHASE_PENDING = 2;        // reserved (Ask-to-Buy / Google PENDING)
        }
        """
        arg = to_message(clouddrive.pb2.VerifyStorePurchaseRequest, arg)
        if async_:
            return self.async_stub.VerifyStorePurchase(arg, metadata=self.metadata)
        else:
            return self.stub.VerifyStorePurchase(arg, metadata=self.metadata)

    @overload
    def GetReferralCode(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.StringValue:
        ...
    @overload
    def GetReferralCode(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.StringValue]:
        ...
    def GetReferralCode(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.StringValue | Coroutine[Any, Any, clouddrive.pb2.StringValue]:
        """
        get referral code of current user

        ------------------- protobuf rpc definition --------------------

        // get referral code of current user
        rpc GetReferralCode(google.protobuf.Empty) returns (StringValue) {}

        ------------------- protobuf type definition -------------------

        message StringValue { string value = 1; }
        """
        if async_:
            return self.async_stub.GetReferralCode(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetReferralCode(Empty(), metadata=self.metadata)

    @overload
    def BackupGetAll(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.BackupList:
        ...
    @overload
    def BackupGetAll(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.BackupList]:
        ...
    def BackupGetAll(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.BackupList | Coroutine[Any, Any, clouddrive.pb2.BackupList]:
        """
        list all backups

        ------------------- protobuf rpc definition --------------------

        // list all backups
        rpc BackupGetAll(google.protobuf.Empty) returns (BackupList) {}

        ------------------- protobuf type definition -------------------

        message BackupList { repeated BackupStatus backups = 1; }
        message BackupStatus {
          enum Status {
            Idle = 0;
            WalkingThrough = 1;
            Error = 2;
            Disabled = 3;
            Scanned = 4;
            Finished = 5;
            // Scan is queued/paused (issue #462): waiting for a walker slot or for the
            // transfer queue to drain. Clients show this as \"Pending\".
            Waiting = 6;
          }
          enum FileWatchStatus {
            WatcherIdle = 0;
            Watching = 1;
            WatcherError = 2;
            WatcherDisabled = 3;
          }
          Backup backup = 1;
          Status status = 2;
          string statusMessage = 3;
          FileWatchStatus watcherStatus = 4;
          string watcherStatusMessage = 5;
          repeated TaskError errors = 7;
        }
        """
        if async_:
            return self.async_stub.BackupGetAll(Empty(), metadata=self.metadata)
        else:
            return self.stub.BackupGetAll(Empty(), metadata=self.metadata)

    @overload
    def BackupGetStatus(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.BackupStatus:
        ...
    @overload
    def BackupGetStatus(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.BackupStatus]:
        ...
    def BackupGetStatus(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.BackupStatus | Coroutine[Any, Any, clouddrive.pb2.BackupStatus]:
        """
        get backup status

        ------------------- protobuf rpc definition --------------------

        // get backup status
        rpc BackupGetStatus(StringValue) returns (BackupStatus) {}

        ------------------- protobuf type definition -------------------

        message BackupStatus {
          enum Status {
            Idle = 0;
            WalkingThrough = 1;
            Error = 2;
            Disabled = 3;
            Scanned = 4;
            Finished = 5;
            // Scan is queued/paused (issue #462): waiting for a walker slot or for the
            // transfer queue to drain. Clients show this as \"Pending\".
            Waiting = 6;
          }
          enum FileWatchStatus {
            WatcherIdle = 0;
            Watching = 1;
            WatcherError = 2;
            WatcherDisabled = 3;
          }
          Backup backup = 1;
          Status status = 2;
          string statusMessage = 3;
          FileWatchStatus watcherStatus = 4;
          string watcherStatusMessage = 5;
          repeated TaskError errors = 7;
        }
        message StringValue { string value = 1; }
        message TaskError {
          google.protobuf.Timestamp time = 1;
          string message = 2;
        }
        """
        arg = to_message(clouddrive.pb2.StringValue, arg)
        if async_:
            return self.async_stub.BackupGetStatus(arg, metadata=self.metadata)
        else:
            return self.stub.BackupGetStatus(arg, metadata=self.metadata)

    @overload
    def BackupAdd(
        self, 
        arg: dict | clouddrive.pb2.Backup, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def BackupAdd(
        self, 
        arg: dict | clouddrive.pb2.Backup, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def BackupAdd(
        self, 
        arg: dict | clouddrive.pb2.Backup, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        add a backup

        ------------------- protobuf rpc definition --------------------

        // add a backup
        rpc BackupAdd(Backup) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message Backup {
          string sourcePath = 1;
          repeated BackupDestination destinations = 2;
          repeated FileBackupRule fileBackupRules = 3;
          FileReplaceRule fileReplaceRule = 4;
          FileDeleteRule fileDeleteRule = 5;
          FileCompletionRule fileCompletionRule = 13;
          bool isEnabled = 6;
          bool fileSystemWatchEnabled = 7;
          int64 walkingThroughIntervalSecs = 8; // 0 means never auto walking through
          bool forceWalkingThroughOnStart = 9;
          repeated TimeSchedule timeSchedules = 10;
          bool isTimeSchedulesEnabled = 11;
          bool syncDeleteFromDest = 14; // Delete files/folders from destination that don't exist in source while walking through
          optional bool dontStartScanAfterAdd = 15; // If set to true, don't auto start full scan after backup is added. Default (false/unset) scans immediately.
        }
        message BackupDestination {
          string destinationPath = 1;
          bool isEnabled = 2;
          optional google.protobuf.Timestamp lastFinishTime = 3;
        }
        message FileBackupRule {
          oneof rule {
            string extensions = 1;
            string fileNames = 2;
            string regex = 3;
            uint64 minSize = 4;
          }
          bool isEnabled = 100;
          bool isBlackList = 101;
          bool applyToFolder = 102;
          // If present, determines whether rule applies to regular files; default true
          // when absent
          optional bool applyToFile = 103;
        }
        enum FileCompletionRule {
          None = 0;
          DeleteSource = 1;
          DeleteSourceAndEmptyFolder = 2;
        }
        enum FileDeleteRule {
          Delete = 0;
          Recycle = 1;
          Keep = 2;
          MoveToVersionHistory = 3;
        }
        enum FileReplaceRule {
          Skip = 0;
          Overwrite = 1;
          KeepHistoryVersion = 2;
        }
        message TimeSchedule {
          bool isEnabled = 1;
          uint32 hour = 2;
          uint32 minute = 3;
          uint32 second = 4;
          optional DaysOfWeek daysOfWeek = 5; // none means every day
        }
        """
        if async_:
            async def request():
                await self.async_stub.BackupAdd(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.BackupAdd(arg, metadata=self.metadata)
            return None

    @overload
    def BackupRemove(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def BackupRemove(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def BackupRemove(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        remove a backup by it's source path

        ------------------- protobuf rpc definition --------------------

        // remove a backup by it's source path
        rpc BackupRemove(StringValue) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message StringValue { string value = 1; }
        """
        if async_:
            async def request():
                await self.async_stub.BackupRemove(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.BackupRemove(arg, metadata=self.metadata)
            return None

    @overload
    def BackupUpdate(
        self, 
        arg: dict | clouddrive.pb2.Backup, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def BackupUpdate(
        self, 
        arg: dict | clouddrive.pb2.Backup, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def BackupUpdate(
        self, 
        arg: dict | clouddrive.pb2.Backup, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        update a backup

        ------------------- protobuf rpc definition --------------------

        // update a backup
        rpc BackupUpdate(Backup) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message Backup {
          string sourcePath = 1;
          repeated BackupDestination destinations = 2;
          repeated FileBackupRule fileBackupRules = 3;
          FileReplaceRule fileReplaceRule = 4;
          FileDeleteRule fileDeleteRule = 5;
          FileCompletionRule fileCompletionRule = 13;
          bool isEnabled = 6;
          bool fileSystemWatchEnabled = 7;
          int64 walkingThroughIntervalSecs = 8; // 0 means never auto walking through
          bool forceWalkingThroughOnStart = 9;
          repeated TimeSchedule timeSchedules = 10;
          bool isTimeSchedulesEnabled = 11;
          bool syncDeleteFromDest = 14; // Delete files/folders from destination that don't exist in source while walking through
          optional bool dontStartScanAfterAdd = 15; // If set to true, don't auto start full scan after backup is added. Default (false/unset) scans immediately.
        }
        message BackupDestination {
          string destinationPath = 1;
          bool isEnabled = 2;
          optional google.protobuf.Timestamp lastFinishTime = 3;
        }
        message FileBackupRule {
          oneof rule {
            string extensions = 1;
            string fileNames = 2;
            string regex = 3;
            uint64 minSize = 4;
          }
          bool isEnabled = 100;
          bool isBlackList = 101;
          bool applyToFolder = 102;
          // If present, determines whether rule applies to regular files; default true
          // when absent
          optional bool applyToFile = 103;
        }
        enum FileCompletionRule {
          None = 0;
          DeleteSource = 1;
          DeleteSourceAndEmptyFolder = 2;
        }
        enum FileDeleteRule {
          Delete = 0;
          Recycle = 1;
          Keep = 2;
          MoveToVersionHistory = 3;
        }
        enum FileReplaceRule {
          Skip = 0;
          Overwrite = 1;
          KeepHistoryVersion = 2;
        }
        message TimeSchedule {
          bool isEnabled = 1;
          uint32 hour = 2;
          uint32 minute = 3;
          uint32 second = 4;
          optional DaysOfWeek daysOfWeek = 5; // none means every day
        }
        """
        if async_:
            async def request():
                await self.async_stub.BackupUpdate(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.BackupUpdate(arg, metadata=self.metadata)
            return None

    @overload
    def BackupAddDestination(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def BackupAddDestination(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def BackupAddDestination(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        add destinations to a backup

        ------------------- protobuf rpc definition --------------------

        // add destinations to a backup
        rpc BackupAddDestination(BackupModifyRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message BackupDestination {
          string destinationPath = 1;
          bool isEnabled = 2;
          optional google.protobuf.Timestamp lastFinishTime = 3;
        }
        message BackupModifyRequest {
          string sourcePath = 1;
          repeated BackupDestination destinations = 2;
          repeated FileBackupRule fileBackupRules = 3;
          optional FileReplaceRule fileReplaceRule = 4;
          optional FileDeleteRule fileDeleteRule = 5;
          optional bool fileSystemWatchEnabled = 6;
          optional int64 walkingThroughIntervalSecs = 7;
        }
        message FileBackupRule {
          oneof rule {
            string extensions = 1;
            string fileNames = 2;
            string regex = 3;
            uint64 minSize = 4;
          }
          bool isEnabled = 100;
          bool isBlackList = 101;
          bool applyToFolder = 102;
          // If present, determines whether rule applies to regular files; default true
          // when absent
          optional bool applyToFile = 103;
        }
        enum FileDeleteRule {
          Delete = 0;
          Recycle = 1;
          Keep = 2;
          MoveToVersionHistory = 3;
        }
        enum FileReplaceRule {
          Skip = 0;
          Overwrite = 1;
          KeepHistoryVersion = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.BackupAddDestination(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.BackupAddDestination(arg, metadata=self.metadata)
            return None

    @overload
    def BackupRemoveDestination(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def BackupRemoveDestination(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def BackupRemoveDestination(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        remove destinations from a backup

        ------------------- protobuf rpc definition --------------------

        // remove destinations from a backup
        rpc BackupRemoveDestination(BackupModifyRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message BackupDestination {
          string destinationPath = 1;
          bool isEnabled = 2;
          optional google.protobuf.Timestamp lastFinishTime = 3;
        }
        message BackupModifyRequest {
          string sourcePath = 1;
          repeated BackupDestination destinations = 2;
          repeated FileBackupRule fileBackupRules = 3;
          optional FileReplaceRule fileReplaceRule = 4;
          optional FileDeleteRule fileDeleteRule = 5;
          optional bool fileSystemWatchEnabled = 6;
          optional int64 walkingThroughIntervalSecs = 7;
        }
        message FileBackupRule {
          oneof rule {
            string extensions = 1;
            string fileNames = 2;
            string regex = 3;
            uint64 minSize = 4;
          }
          bool isEnabled = 100;
          bool isBlackList = 101;
          bool applyToFolder = 102;
          // If present, determines whether rule applies to regular files; default true
          // when absent
          optional bool applyToFile = 103;
        }
        enum FileDeleteRule {
          Delete = 0;
          Recycle = 1;
          Keep = 2;
          MoveToVersionHistory = 3;
        }
        enum FileReplaceRule {
          Skip = 0;
          Overwrite = 1;
          KeepHistoryVersion = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.BackupRemoveDestination(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.BackupRemoveDestination(arg, metadata=self.metadata)
            return None

    @overload
    def BackupSetEnabled(
        self, 
        arg: dict | clouddrive.pb2.BackupSetEnabledRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def BackupSetEnabled(
        self, 
        arg: dict | clouddrive.pb2.BackupSetEnabledRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def BackupSetEnabled(
        self, 
        arg: dict | clouddrive.pb2.BackupSetEnabledRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        enable/disable a backup

        ------------------- protobuf rpc definition --------------------

        // enable/disable a backup
        rpc BackupSetEnabled(BackupSetEnabledRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message BackupSetEnabledRequest {
          string sourcePath = 1;
          bool isEnabled = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.BackupSetEnabled(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.BackupSetEnabled(arg, metadata=self.metadata)
            return None

    @overload
    def BackupSetFileSystemWatchEnabled(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def BackupSetFileSystemWatchEnabled(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def BackupSetFileSystemWatchEnabled(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        enable/disable a backup's FileSystemWatch

        ------------------- protobuf rpc definition --------------------

        // enable/disable a backup's FileSystemWatch
        rpc BackupSetFileSystemWatchEnabled(BackupModifyRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message BackupDestination {
          string destinationPath = 1;
          bool isEnabled = 2;
          optional google.protobuf.Timestamp lastFinishTime = 3;
        }
        message BackupModifyRequest {
          string sourcePath = 1;
          repeated BackupDestination destinations = 2;
          repeated FileBackupRule fileBackupRules = 3;
          optional FileReplaceRule fileReplaceRule = 4;
          optional FileDeleteRule fileDeleteRule = 5;
          optional bool fileSystemWatchEnabled = 6;
          optional int64 walkingThroughIntervalSecs = 7;
        }
        message FileBackupRule {
          oneof rule {
            string extensions = 1;
            string fileNames = 2;
            string regex = 3;
            uint64 minSize = 4;
          }
          bool isEnabled = 100;
          bool isBlackList = 101;
          bool applyToFolder = 102;
          // If present, determines whether rule applies to regular files; default true
          // when absent
          optional bool applyToFile = 103;
        }
        enum FileDeleteRule {
          Delete = 0;
          Recycle = 1;
          Keep = 2;
          MoveToVersionHistory = 3;
        }
        enum FileReplaceRule {
          Skip = 0;
          Overwrite = 1;
          KeepHistoryVersion = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.BackupSetFileSystemWatchEnabled(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.BackupSetFileSystemWatchEnabled(arg, metadata=self.metadata)
            return None

    @overload
    def BackupUpdateStrategies(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def BackupUpdateStrategies(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def BackupUpdateStrategies(
        self, 
        arg: dict | clouddrive.pb2.BackupModifyRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        deprecated, use BackupUpdate instead

        ------------------- protobuf rpc definition --------------------

        // deprecated, use BackupUpdate instead
        rpc BackupUpdateStrategies(BackupModifyRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message BackupDestination {
          string destinationPath = 1;
          bool isEnabled = 2;
          optional google.protobuf.Timestamp lastFinishTime = 3;
        }
        message BackupModifyRequest {
          string sourcePath = 1;
          repeated BackupDestination destinations = 2;
          repeated FileBackupRule fileBackupRules = 3;
          optional FileReplaceRule fileReplaceRule = 4;
          optional FileDeleteRule fileDeleteRule = 5;
          optional bool fileSystemWatchEnabled = 6;
          optional int64 walkingThroughIntervalSecs = 7;
        }
        message FileBackupRule {
          oneof rule {
            string extensions = 1;
            string fileNames = 2;
            string regex = 3;
            uint64 minSize = 4;
          }
          bool isEnabled = 100;
          bool isBlackList = 101;
          bool applyToFolder = 102;
          // If present, determines whether rule applies to regular files; default true
          // when absent
          optional bool applyToFile = 103;
        }
        enum FileDeleteRule {
          Delete = 0;
          Recycle = 1;
          Keep = 2;
          MoveToVersionHistory = 3;
        }
        enum FileReplaceRule {
          Skip = 0;
          Overwrite = 1;
          KeepHistoryVersion = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.BackupUpdateStrategies(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.BackupUpdateStrategies(arg, metadata=self.metadata)
            return None

    @overload
    def BackupRestartWalkingThrough(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def BackupRestartWalkingThrough(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def BackupRestartWalkingThrough(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        restart a backup walking through

        ------------------- protobuf rpc definition --------------------

        // restart a backup walking through
        rpc BackupRestartWalkingThrough(StringValue) returns (google.protobuf.Empty) {
        }

        ------------------- protobuf type definition -------------------

        message StringValue { string value = 1; }
        """
        if async_:
            async def request():
                await self.async_stub.BackupRestartWalkingThrough(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.BackupRestartWalkingThrough(arg, metadata=self.metadata)
            return None

    @overload
    def CanAddMoreBackups(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileOperationResult:
        ...
    @overload
    def CanAddMoreBackups(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        ...
    def CanAddMoreBackups(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileOperationResult | Coroutine[Any, Any, clouddrive.pb2.FileOperationResult]:
        """
        check if current plan can support more backups

        ------------------- protobuf rpc definition --------------------

        // check if current plan can support more backups
        rpc CanAddMoreBackups(google.protobuf.Empty) returns (FileOperationResult) {}

        ------------------- protobuf type definition -------------------

        message FileOperationResult {
          bool success = 1;
          string errorMessage = 2;
          repeated string resultFilePaths = 3;
        }
        """
        if async_:
            return self.async_stub.CanAddMoreBackups(Empty(), metadata=self.metadata)
        else:
            return self.stub.CanAddMoreBackups(Empty(), metadata=self.metadata)

    @overload
    def NotifyPhotoLibraryChanges(
        self, 
        arg: dict | clouddrive.pb2.PhotoLibraryChangeList, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def NotifyPhotoLibraryChanges(
        self, 
        arg: dict | clouddrive.pb2.PhotoLibraryChangeList, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def NotifyPhotoLibraryChanges(
        self, 
        arg: dict | clouddrive.pb2.PhotoLibraryChangeList, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        notify about new photos for backup (iOS/mobile platform integration)

        ------------------- protobuf rpc definition --------------------

        // notify about new photos for backup (iOS/mobile platform integration)
        rpc NotifyPhotoLibraryChanges(PhotoLibraryChangeList) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        // Photo Library Integration (iOS/Mobile)
        message PhotoLibraryChange {
          enum ChangeType {
            Create = 0;
            Delete = 1;
          }
          ChangeType changeType = 1;
          string localFilePath = 2; // Path in app's sandbox where photo was exported
          string originalIdentifier = 3; // PHAsset localIdentifier for tracking
          optional string originalFileName = 4;
          optional google.protobuf.Timestamp creationDate = 5;
        }
        message PhotoLibraryChangeList {
          repeated PhotoLibraryChange changes = 1;
          string backupSourcePath = 2; // The backup source path to notify (e.g., \"Photos\")
        }
        """
        if async_:
            async def request():
                await self.async_stub.NotifyPhotoLibraryChanges(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.NotifyPhotoLibraryChanges(arg, metadata=self.metadata)
            return None

    @overload
    def GetMachineId(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.StringResult:
        ...
    @overload
    def GetMachineId(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.StringResult]:
        ...
    def GetMachineId(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.StringResult | Coroutine[Any, Any, clouddrive.pb2.StringResult]:
        """
        get machine id

        ------------------- protobuf rpc definition --------------------

        // get machine id
        rpc GetMachineId(google.protobuf.Empty) returns (StringResult) {}

        ------------------- protobuf type definition -------------------

        message StringResult { string result = 1; }
        """
        if async_:
            return self.async_stub.GetMachineId(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetMachineId(Empty(), metadata=self.metadata)

    @overload
    def GetOnlineDevices(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.OnlineDevices:
        ...
    @overload
    def GetOnlineDevices(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.OnlineDevices]:
        ...
    def GetOnlineDevices(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.OnlineDevices | Coroutine[Any, Any, clouddrive.pb2.OnlineDevices]:
        """
        get online devices

        ------------------- protobuf rpc definition --------------------

        // get online devices
        rpc GetOnlineDevices(google.protobuf.Empty) returns (OnlineDevices) {}

        ------------------- protobuf type definition -------------------

        message Device {
          string deviceId = 1;
          string deviceName = 2;
          string osType = 3;
          string version = 4;
          string ipAddress = 5;
          google.protobuf.Timestamp lastUpdateTime = 6;
        }
        message OnlineDevices { repeated Device devices = 1; }
        """
        if async_:
            return self.async_stub.GetOnlineDevices(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetOnlineDevices(Empty(), metadata=self.metadata)

    @overload
    def KickoutDevice(
        self, 
        arg: dict | clouddrive.pb2.DeviceRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def KickoutDevice(
        self, 
        arg: dict | clouddrive.pb2.DeviceRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def KickoutDevice(
        self, 
        arg: dict | clouddrive.pb2.DeviceRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        kickout a device

        ------------------- protobuf rpc definition --------------------

        // kickout a device
        rpc KickoutDevice(DeviceRequest) returns (google.protobuf.Empty) {
        }

        ------------------- protobuf type definition -------------------

        message DeviceRequest { string deviceId = 1; }
        """
        if async_:
            async def request():
                await self.async_stub.KickoutDevice(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.KickoutDevice(arg, metadata=self.metadata)
            return None

    @overload
    def ListLogFiles(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.ListLogFileResult:
        ...
    @overload
    def ListLogFiles(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.ListLogFileResult]:
        ...
    def ListLogFiles(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.ListLogFileResult | Coroutine[Any, Any, clouddrive.pb2.ListLogFileResult]:
        """
        list log file names

        ------------------- protobuf rpc definition --------------------

        // list log file names
        rpc ListLogFiles(google.protobuf.Empty) returns (ListLogFileResult) {}

        ------------------- protobuf type definition -------------------

        message ListLogFileResult { repeated LogFileRecord logFiles = 1; }
        message LogFileRecord {
          string fileName = 1;
          google.protobuf.Timestamp lastModifiedTime = 2;
          uint64 fileSize = 3;
          string signature = 4;
        }
        """
        if async_:
            return self.async_stub.ListLogFiles(Empty(), metadata=self.metadata)
        else:
            return self.stub.ListLogFiles(Empty(), metadata=self.metadata)

    @overload
    def SyncFileChangesFromCloud(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.FileSystemChangeStatistics:
        ...
    @overload
    def SyncFileChangesFromCloud(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.FileSystemChangeStatistics]:
        ...
    def SyncFileChangesFromCloud(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.FileSystemChangeStatistics | Coroutine[Any, Any, clouddrive.pb2.FileSystemChangeStatistics]:
        """
        sync file changes from cloud

        ------------------- protobuf rpc definition --------------------

        // sync file changes from cloud
        rpc SyncFileChangesFromCloud(FileRequest)
            returns (FileSystemChangeStatistics) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        message FileSystemChangeStatistics {
          uint64 createCount = 1;
          uint64 deleteCount = 2;
          uint64 renameCount = 3;
        }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.SyncFileChangesFromCloud(arg, metadata=self.metadata)
        else:
            return self.stub.SyncFileChangesFromCloud(arg, metadata=self.metadata)

    @overload
    def StartCloudEventListener(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def StartCloudEventListener(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def StartCloudEventListener(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        start cloud events listener

        ------------------- protobuf rpc definition --------------------

        // start cloud events listener
        rpc StartCloudEventListener(FileRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        if async_:
            async def request():
                await self.async_stub.StartCloudEventListener(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.StartCloudEventListener(arg, metadata=self.metadata)
            return None

    @overload
    def StopCloudEventListener(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def StopCloudEventListener(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def StopCloudEventListener(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        stop cloud events listener

        ------------------- protobuf rpc definition --------------------

        // stop cloud events listener
        rpc StopCloudEventListener(FileRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        """
        if async_:
            async def request():
                await self.async_stub.StopCloudEventListener(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.StopCloudEventListener(arg, metadata=self.metadata)
            return None

    @overload
    def WalkThroughFolderTest(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.WalkThroughFolderResult:
        ...
    @overload
    def WalkThroughFolderTest(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.WalkThroughFolderResult]:
        ...
    def WalkThroughFolderTest(
        self, 
        arg: dict | clouddrive.pb2.FileRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.WalkThroughFolderResult | Coroutine[Any, Any, clouddrive.pb2.WalkThroughFolderResult]:
        """
        walk through folder test

        ------------------- protobuf rpc definition --------------------

        // walk through folder test
        rpc WalkThroughFolderTest(FileRequest) returns (WalkThroughFolderResult) {}

        ------------------- protobuf type definition -------------------

        message FileRequest {
          string path = 1;
          optional bool forceRefresh = 2; // if true, will force refresh the file info
        }
        message WalkThroughFolderResult {
          uint64 totalFolderCount = 1;
          uint64 totalFileCount = 2;
          uint64 totalSize = 3;
        }
        """
        arg = to_message(clouddrive.pb2.FileRequest, arg)
        if async_:
            return self.async_stub.WalkThroughFolderTest(arg, metadata=self.metadata)
        else:
            return self.stub.WalkThroughFolderTest(arg, metadata=self.metadata)

    @overload
    def GetWebhookConfigTemplate(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.StringResult:
        ...
    @overload
    def GetWebhookConfigTemplate(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.StringResult]:
        ...
    def GetWebhookConfigTemplate(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.StringResult | Coroutine[Any, Any, clouddrive.pb2.StringResult]:
        """
        get a webhook config template

        ------------------- protobuf rpc definition --------------------

        // get a webhook config template
        rpc GetWebhookConfigTemplate(google.protobuf.Empty) returns (StringResult) {}

        ------------------- protobuf type definition -------------------

        message StringResult { string result = 1; }
        """
        if async_:
            return self.async_stub.GetWebhookConfigTemplate(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetWebhookConfigTemplate(Empty(), metadata=self.metadata)

    @overload
    def GetWebhookConfigs(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.WebhookList:
        ...
    @overload
    def GetWebhookConfigs(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.WebhookList]:
        ...
    def GetWebhookConfigs(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.WebhookList | Coroutine[Any, Any, clouddrive.pb2.WebhookList]:
        """
        list all webhook configs

        ------------------- protobuf rpc definition --------------------

        // list all webhook configs
        rpc GetWebhookConfigs(google.protobuf.Empty) returns (WebhookList) {}

        ------------------- protobuf type definition -------------------

        message WebhookInfo {
          string fileName = 1;
          string content = 2;
          bool isValid = 3;
        }
        message WebhookList { repeated WebhookInfo webhooks = 1; }
        """
        if async_:
            return self.async_stub.GetWebhookConfigs(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetWebhookConfigs(Empty(), metadata=self.metadata)

    @overload
    def AddWebhookConfig(
        self, 
        arg: dict | clouddrive.pb2.WebhookRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def AddWebhookConfig(
        self, 
        arg: dict | clouddrive.pb2.WebhookRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def AddWebhookConfig(
        self, 
        arg: dict | clouddrive.pb2.WebhookRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        add webhook config

        ------------------- protobuf rpc definition --------------------

        // add webhook config
        rpc AddWebhookConfig(WebhookRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message WebhookRequest {
          string fileName = 1;
          string content = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.AddWebhookConfig(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.AddWebhookConfig(arg, metadata=self.metadata)
            return None

    @overload
    def RemoveWebhookConfig(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RemoveWebhookConfig(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RemoveWebhookConfig(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        remove webhook config

        ------------------- protobuf rpc definition --------------------

        // remove webhook config
        rpc RemoveWebhookConfig(StringValue) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message StringValue { string value = 1; }
        """
        if async_:
            async def request():
                await self.async_stub.RemoveWebhookConfig(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RemoveWebhookConfig(arg, metadata=self.metadata)
            return None

    @overload
    def ChangeWebhookConfig(
        self, 
        arg: dict | clouddrive.pb2.WebhookRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ChangeWebhookConfig(
        self, 
        arg: dict | clouddrive.pb2.WebhookRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ChangeWebhookConfig(
        self, 
        arg: dict | clouddrive.pb2.WebhookRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        change webhook content

        ------------------- protobuf rpc definition --------------------

        // change webhook content
        rpc ChangeWebhookConfig(WebhookRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message WebhookRequest {
          string fileName = 1;
          string content = 2;
        }
        """
        if async_:
            async def request():
                await self.async_stub.ChangeWebhookConfig(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ChangeWebhookConfig(arg, metadata=self.metadata)
            return None

    @overload
    def AddDavUser(
        self, 
        arg: dict | clouddrive.pb2.AddDavUserRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def AddDavUser(
        self, 
        arg: dict | clouddrive.pb2.AddDavUserRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def AddDavUser(
        self, 
        arg: dict | clouddrive.pb2.AddDavUserRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        DAV User Management
        add a new DAV user

        ------------------- protobuf rpc definition --------------------

        // DAV User Management
        // add a new DAV user
        rpc AddDavUser(AddDavUserRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        // DAV User Management
        message AddDavUserRequest {
          string userName = 1;
          string password = 2;
          optional string rootPath = 3;
          optional bool readOnly = 4;
          optional bool enabled = 5;
          optional bool guest = 6;
        }
        """
        if async_:
            async def request():
                await self.async_stub.AddDavUser(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.AddDavUser(arg, metadata=self.metadata)
            return None

    @overload
    def RemoveDavUser(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RemoveDavUser(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RemoveDavUser(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        remove a DAV user

        ------------------- protobuf rpc definition --------------------

        // remove a DAV user
        rpc RemoveDavUser(StringValue) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message StringValue { string value = 1; }
        """
        if async_:
            async def request():
                await self.async_stub.RemoveDavUser(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RemoveDavUser(arg, metadata=self.metadata)
            return None

    @overload
    def ModifyDavUser(
        self, 
        arg: dict | clouddrive.pb2.ModifyDavUserRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def ModifyDavUser(
        self, 
        arg: dict | clouddrive.pb2.ModifyDavUserRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def ModifyDavUser(
        self, 
        arg: dict | clouddrive.pb2.ModifyDavUserRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        modify DAV user settings

        ------------------- protobuf rpc definition --------------------

        // modify DAV user settings
        rpc ModifyDavUser(ModifyDavUserRequest) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message ModifyDavUserRequest {
          string userName = 1;
          optional string password = 2;
          optional string rootPath = 3;
          optional bool readOnly = 4;
          optional bool enabled = 5;
          optional bool guest = 6;
        }
        """
        if async_:
            async def request():
                await self.async_stub.ModifyDavUser(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.ModifyDavUser(arg, metadata=self.metadata)
            return None

    @overload
    def GetDavUser(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.DavUser:
        ...
    @overload
    def GetDavUser(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.DavUser]:
        ...
    def GetDavUser(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.DavUser | Coroutine[Any, Any, clouddrive.pb2.DavUser]:
        """
        get DAV user by username

        ------------------- protobuf rpc definition --------------------

        // get DAV user by username
        rpc GetDavUser(StringValue) returns (DavUser) {}

        ------------------- protobuf type definition -------------------

        message DavUser {
          string userName = 1;
          string password = 2;
          string rootPath = 3;
          bool readOnly = 4;
          bool enabled = 5;
          bool guest = 6;
        }
        message StringValue { string value = 1; }
        """
        arg = to_message(clouddrive.pb2.StringValue, arg)
        if async_:
            return self.async_stub.GetDavUser(arg, metadata=self.metadata)
        else:
            return self.stub.GetDavUser(arg, metadata=self.metadata)

    @overload
    def GetDavServerConfig(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.DavServerConfig:
        ...
    @overload
    def GetDavServerConfig(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.DavServerConfig]:
        ...
    def GetDavServerConfig(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.DavServerConfig | Coroutine[Any, Any, clouddrive.pb2.DavServerConfig]:
        """
        list all DAV users

        ------------------- protobuf rpc definition --------------------

        // list all DAV users
        rpc GetDavServerConfig(google.protobuf.Empty) returns (DavServerConfig) {}

        ------------------- protobuf type definition -------------------

        message DavServerConfig {
          bool davServerEnabled = 1; // if true, enable DAV server
          string davServerPath = 2; // currently fixed to \"/dav\"
          bool enableClouddriveAccount =
              3; // if true, enable cloud drive account as webdav user
          string clouddriveAccountRootPath =
              4; // root path for cloud drive account, if empty, use default path \"/\"
          bool clouddriveAccountReadOnly =
              5; // if true, cloud drive account is read-only, default is false
          bool enableAnonymousAccess = 6; // if true, enable anonymous access
          string anonymousRootPath =
              7; // root path for anonymous access, if empty, use default path \"/\"
          bool anonymousReadOnly =
              8; // if true, anonymous access is read-only, default is true
          repeated DavUser users = 9;
          bool enableAccessLog = 10; // if true, log WebDAV access to webdav-YYYY-MM-DD.log
        }
        message DavUser {
          string userName = 1;
          string password = 2;
          string rootPath = 3;
          bool readOnly = 4;
          bool enabled = 5;
          bool guest = 6;
        }
        """
        if async_:
            return self.async_stub.GetDavServerConfig(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetDavServerConfig(Empty(), metadata=self.metadata)

    @overload
    def SetDavServerConfig(
        self, 
        arg: dict | clouddrive.pb2.ModifyDavServerConfigRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SetDavServerConfig(
        self, 
        arg: dict | clouddrive.pb2.ModifyDavServerConfigRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SetDavServerConfig(
        self, 
        arg: dict | clouddrive.pb2.ModifyDavServerConfigRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        enable/disable DAV server

        ------------------- protobuf rpc definition --------------------

        // enable/disable DAV server
        rpc SetDavServerConfig(ModifyDavServerConfigRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message ModifyDavServerConfigRequest {
          optional bool enableDavServer = 1;
          optional bool enableClouddriveAccount =
              2; // if true, enable cloud drive account as webdav user
          optional string clouddriveAccountRootPath = 3; // root path for cloud
          optional bool clouddriveAccountReadOnly =
              4; // if true, cloud drive account is read-only
          optional bool enableAnonymousAccess = 5; // if true, enable anonymous access
          optional string anonymousRootPath = 6;   // if empty, use default path
          optional bool anonymousReadOnly = 7; // if true, anonymous access is read-only
          optional bool enableAccessLog = 8; // if true, log WebDAV access
        }

        // --- Remote Upload Protocol Messages ---
        """
        if async_:
            async def request():
                await self.async_stub.SetDavServerConfig(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SetDavServerConfig(arg, metadata=self.metadata)
            return None

    @overload
    def CreateToken(
        self, 
        arg: dict | clouddrive.pb2.CreateTokenRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.TokenInfo:
        ...
    @overload
    def CreateToken(
        self, 
        arg: dict | clouddrive.pb2.CreateTokenRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.TokenInfo]:
        ...
    def CreateToken(
        self, 
        arg: dict | clouddrive.pb2.CreateTokenRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.TokenInfo | Coroutine[Any, Any, clouddrive.pb2.TokenInfo]:
        """
        Token management (admin only)

        ------------------- protobuf rpc definition --------------------

        // Token management (admin only)
        rpc CreateToken(CreateTokenRequest) returns (TokenInfo) {}

        ------------------- protobuf type definition -------------------

        message CreateTokenRequest {
          string rootDir = 1;
          TokenPermissions permissions = 2;
          string friendly_name = 3;
          // seconds from now until expiration. If absent or 0, never expires.
          optional uint64 expires_in = 4;
          optional bool enableGrpcLog = 5; // if true, log gRPC access (default: true for user tokens)
          optional bool enableStreamFileLog = 6; // if true, log stream file access (default: true for user tokens)
        }
        message TokenInfo {
          string token = 1;
          string rootDir = 2;
          TokenPermissions permissions = 3;
          // seconds from now until expiration. If absent or 0, the token never expires.
          optional uint64 expires_in = 4;
          string friendly_name = 5;
          bool enableGrpcLog = 6; // if true, log gRPC access to api_token-YYYY-MM-DD.log (default: false for admin tokens, true for user tokens)
          bool enableStreamFileLog = 7; // if true, log stream file access to api_token-YYYY-MM-DD.log (default: false for admin tokens, true for user tokens)
        }
        // --- End Remote Upload Protocol Messages ---
        message TokenPermissions {
          // File Operations
          bool allow_list = 1; // GetSubFiles, FindFileByPath
          bool allow_search = 2; // GetSearchResults
          bool allow_list_local =
              3; // LocalGetSubFiles, GetAvailableDriveLetters, HasDriveLetters
          bool allow_create_folder = 4; // CreateFolder, CreateEncryptedFolder
          bool allow_create_file = 5; // CreateFile, WriteToFile, WriteToFileStream
          bool allow_write = 6; // File uploads and copy operations
          bool allow_read = 7; // File downloads
          bool allow_rename = 8; // RenameFile, RenameFiles
          bool allow_move = 9; // MoveFile
          bool allow_copy = 10; // CopyFile
          bool allow_delete = 11; // DeleteFile, DeleteFiles
          bool allow_delete_permanently =
              12; // DeleteFilePermanently, DeleteFilesPermanently

          // Encryption Operations
          bool allow_create_encrypt = 13; // CreateEncryptedFolder
          bool allow_unlock_encrypted = 14; // UnlockEncryptedFile
          bool allow_lock_encrypted = 15; // LockEncryptedFile

          // Cloud Operations
          bool allow_add_offline_download = 16; // AddOfflineFiles
          bool allow_list_offline_downloads =
              17; // ListOfflineFilesByPath, ListAllOfflineFiles, GetOfflineQuotaInfo
          bool allow_modify_offline_downloads =
              18; // RemoveOfflineFiles, ClearOfflineFiles, RestartOfflineTask
          bool allow_shared_links = 19; // AddSharedLink

          // System Information
          bool allow_view_properties = 20; // GetFileDetailProperties
          bool allow_get_space_info = 21; // GetSpaceInfo
          bool allow_view_runtime_info = 22; // GetRuntimeInfo, GetRunningInfo
          bool allow_push_message = 41; // Receive push messages (file system changes,
                                        // transfer task updates, etc.)

          // Membership Management
          bool allow_get_memberships = 23; // GetCloudMemberships
          bool allow_modify_memberships =
              24; // Future membership modification operations

          // Mount Management
          bool allow_get_mounts = 25; // GetMountPoints, CanAddMoreMountPoints
          bool allow_modify_mounts =
              26; // AddMountPoint, RemoveMountPoint, Mount, Unmount, UpdateMountPoint

          // Transfer Management
          bool allow_get_transfer_tasks =
              27; // GetAllTasksCount, GetDownloadFileCount, GetDownloadFileList,
                  // GetUploadFileCount, GetUploadFileList, GetCopyTasks, GetMergeTasks
          bool allow_modify_transfer_tasks =
              28; // Cancel/Pause/Resume upload/download/copy operations

          // Cloud API Management
          bool allow_get_cloud_apis =
              29; // GetAllCloudApis, GetCloudAPIConfig, CanAddMoreCloudApis
          bool allow_modify_cloud_apis = 30; // Add/Remove cloud APIs, SetCloudAPIConfig

          // System Settings
          bool allow_get_system_settings =
              31; // GetSystemSettings, GetEffectiveDirCacheTimeSecs, GetDirCacheDbSize, GetVacuumProgress
          bool allow_modify_system_settings =
              32; // SetSystemSettings, SetDirCacheTimeSecs, ForceExpireDirCache, VacuumDirCache

          // Backup Management
          bool allow_get_backups =
              33; // BackupGetAll, BackupGetStatus, CanAddMoreBackups
          bool allow_modify_backups =
              34; // BackupAdd, BackupRemove, BackupUpdate, BackupSetEnabled, etc.

          // DAV Management
          bool allow_get_dav_config = 35; // GetDavUser, GetDavServerConfig
          bool allow_modify_dav_config =
              36; // AddDavUser, RemoveDavUser, ModifyDavUser, SetDavServerConfig

          // Token Management (Admin only)
          bool allow_token_management =
              37; // CreateToken, ModifyToken, RemoveToken, ListTokens

          // Account Management
          bool allow_get_account_info =
              38; // GetAccountStatus, GetBalanceLog, GetReferralCode
          bool allow_modify_account =
              39; // ChangePassword, ChangeEmail, TransferBalance

          // Service Control
          bool allow_service_control = 40; // RestartService, ShutdownService
        }
        """
        arg = to_message(clouddrive.pb2.CreateTokenRequest, arg)
        if async_:
            return self.async_stub.CreateToken(arg, metadata=self.metadata)
        else:
            return self.stub.CreateToken(arg, metadata=self.metadata)

    @overload
    def ModifyToken(
        self, 
        arg: dict | clouddrive.pb2.ModifyTokenRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.TokenInfo:
        ...
    @overload
    def ModifyToken(
        self, 
        arg: dict | clouddrive.pb2.ModifyTokenRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.TokenInfo]:
        ...
    def ModifyToken(
        self, 
        arg: dict | clouddrive.pb2.ModifyTokenRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.TokenInfo | Coroutine[Any, Any, clouddrive.pb2.TokenInfo]:
        """

        ------------------- protobuf rpc definition --------------------

        rpc ModifyToken(ModifyTokenRequest) returns (TokenInfo) {}

        ------------------- protobuf type definition -------------------

        message ModifyTokenRequest {
          string token = 1;
          optional string rootDir = 2;
          optional TokenPermissions permissions = 3;
          optional string friendly_name = 4;
          // Set a new expiration; if set to 0, it will never expire. If absent, keeps
          // existing expiration.
          optional uint64 expires_in = 5;
          optional bool enableGrpcLog = 6; // if true, log gRPC access
          optional bool enableStreamFileLog = 7; // if true, log stream file access
        }
        message TokenInfo {
          string token = 1;
          string rootDir = 2;
          TokenPermissions permissions = 3;
          // seconds from now until expiration. If absent or 0, the token never expires.
          optional uint64 expires_in = 4;
          string friendly_name = 5;
          bool enableGrpcLog = 6; // if true, log gRPC access to api_token-YYYY-MM-DD.log (default: false for admin tokens, true for user tokens)
          bool enableStreamFileLog = 7; // if true, log stream file access to api_token-YYYY-MM-DD.log (default: false for admin tokens, true for user tokens)
        }
        // --- End Remote Upload Protocol Messages ---
        message TokenPermissions {
          // File Operations
          bool allow_list = 1; // GetSubFiles, FindFileByPath
          bool allow_search = 2; // GetSearchResults
          bool allow_list_local =
              3; // LocalGetSubFiles, GetAvailableDriveLetters, HasDriveLetters
          bool allow_create_folder = 4; // CreateFolder, CreateEncryptedFolder
          bool allow_create_file = 5; // CreateFile, WriteToFile, WriteToFileStream
          bool allow_write = 6; // File uploads and copy operations
          bool allow_read = 7; // File downloads
          bool allow_rename = 8; // RenameFile, RenameFiles
          bool allow_move = 9; // MoveFile
          bool allow_copy = 10; // CopyFile
          bool allow_delete = 11; // DeleteFile, DeleteFiles
          bool allow_delete_permanently =
              12; // DeleteFilePermanently, DeleteFilesPermanently

          // Encryption Operations
          bool allow_create_encrypt = 13; // CreateEncryptedFolder
          bool allow_unlock_encrypted = 14; // UnlockEncryptedFile
          bool allow_lock_encrypted = 15; // LockEncryptedFile

          // Cloud Operations
          bool allow_add_offline_download = 16; // AddOfflineFiles
          bool allow_list_offline_downloads =
              17; // ListOfflineFilesByPath, ListAllOfflineFiles, GetOfflineQuotaInfo
          bool allow_modify_offline_downloads =
              18; // RemoveOfflineFiles, ClearOfflineFiles, RestartOfflineTask
          bool allow_shared_links = 19; // AddSharedLink

          // System Information
          bool allow_view_properties = 20; // GetFileDetailProperties
          bool allow_get_space_info = 21; // GetSpaceInfo
          bool allow_view_runtime_info = 22; // GetRuntimeInfo, GetRunningInfo
          bool allow_push_message = 41; // Receive push messages (file system changes,
                                        // transfer task updates, etc.)

          // Membership Management
          bool allow_get_memberships = 23; // GetCloudMemberships
          bool allow_modify_memberships =
              24; // Future membership modification operations

          // Mount Management
          bool allow_get_mounts = 25; // GetMountPoints, CanAddMoreMountPoints
          bool allow_modify_mounts =
              26; // AddMountPoint, RemoveMountPoint, Mount, Unmount, UpdateMountPoint

          // Transfer Management
          bool allow_get_transfer_tasks =
              27; // GetAllTasksCount, GetDownloadFileCount, GetDownloadFileList,
                  // GetUploadFileCount, GetUploadFileList, GetCopyTasks, GetMergeTasks
          bool allow_modify_transfer_tasks =
              28; // Cancel/Pause/Resume upload/download/copy operations

          // Cloud API Management
          bool allow_get_cloud_apis =
              29; // GetAllCloudApis, GetCloudAPIConfig, CanAddMoreCloudApis
          bool allow_modify_cloud_apis = 30; // Add/Remove cloud APIs, SetCloudAPIConfig

          // System Settings
          bool allow_get_system_settings =
              31; // GetSystemSettings, GetEffectiveDirCacheTimeSecs, GetDirCacheDbSize, GetVacuumProgress
          bool allow_modify_system_settings =
              32; // SetSystemSettings, SetDirCacheTimeSecs, ForceExpireDirCache, VacuumDirCache

          // Backup Management
          bool allow_get_backups =
              33; // BackupGetAll, BackupGetStatus, CanAddMoreBackups
          bool allow_modify_backups =
              34; // BackupAdd, BackupRemove, BackupUpdate, BackupSetEnabled, etc.

          // DAV Management
          bool allow_get_dav_config = 35; // GetDavUser, GetDavServerConfig
          bool allow_modify_dav_config =
              36; // AddDavUser, RemoveDavUser, ModifyDavUser, SetDavServerConfig

          // Token Management (Admin only)
          bool allow_token_management =
              37; // CreateToken, ModifyToken, RemoveToken, ListTokens

          // Account Management
          bool allow_get_account_info =
              38; // GetAccountStatus, GetBalanceLog, GetReferralCode
          bool allow_modify_account =
              39; // ChangePassword, ChangeEmail, TransferBalance

          // Service Control
          bool allow_service_control = 40; // RestartService, ShutdownService
        }
        """
        arg = to_message(clouddrive.pb2.ModifyTokenRequest, arg)
        if async_:
            return self.async_stub.ModifyToken(arg, metadata=self.metadata)
        else:
            return self.stub.ModifyToken(arg, metadata=self.metadata)

    @overload
    def RemoveToken(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RemoveToken(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RemoveToken(
        self, 
        arg: dict | clouddrive.pb2.StringValue, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """

        ------------------- protobuf rpc definition --------------------

        rpc RemoveToken(StringValue) returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message StringValue { string value = 1; }
        """
        if async_:
            async def request():
                await self.async_stub.RemoveToken(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RemoveToken(arg, metadata=self.metadata)
            return None

    @overload
    def ListTokens(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.ListTokensResult:
        ...
    @overload
    def ListTokens(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.ListTokensResult]:
        ...
    def ListTokens(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.ListTokensResult | Coroutine[Any, Any, clouddrive.pb2.ListTokensResult]:
        """

        ------------------- protobuf rpc definition --------------------

        rpc ListTokens(google.protobuf.Empty) returns (ListTokensResult) {}

        ------------------- protobuf type definition -------------------

        message ListTokensResult { repeated TokenInfo tokens = 1; }
        message TokenInfo {
          string token = 1;
          string rootDir = 2;
          TokenPermissions permissions = 3;
          // seconds from now until expiration. If absent or 0, the token never expires.
          optional uint64 expires_in = 4;
          string friendly_name = 5;
          bool enableGrpcLog = 6; // if true, log gRPC access to api_token-YYYY-MM-DD.log (default: false for admin tokens, true for user tokens)
          bool enableStreamFileLog = 7; // if true, log stream file access to api_token-YYYY-MM-DD.log (default: false for admin tokens, true for user tokens)
        }
        """
        if async_:
            return self.async_stub.ListTokens(Empty(), metadata=self.metadata)
        else:
            return self.stub.ListTokens(Empty(), metadata=self.metadata)

    @overload
    def GetDownloadUrlPath(
        self, 
        arg: dict | clouddrive.pb2.GetDownloadUrlPathRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.DownloadUrlPathInfo:
        ...
    @overload
    def GetDownloadUrlPath(
        self, 
        arg: dict | clouddrive.pb2.GetDownloadUrlPathRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.DownloadUrlPathInfo]:
        ...
    def GetDownloadUrlPath(
        self, 
        arg: dict | clouddrive.pb2.GetDownloadUrlPathRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.DownloadUrlPathInfo | Coroutine[Any, Any, clouddrive.pb2.DownloadUrlPathInfo]:
        """
        get download URL path and query for a file by path
        to assemble complete URL: combine your gRPC server's scheme://host:port
        with the returned downloadUrlPath example: if gRPC server is
        https://api.example.com:8443 and result is
        \"/static/{SCHEME}/{HOST}/{PREVIEW}/file.txt?token=abc\" then replace
        {SCHEME} with \"https\", {HOST} with \"api.example.com:8443\", and {PREVIEW}
        with \"true\" or \"false\" to get:
        https://api.example.com:8443/static/https/api.example.com:8443/true/file.txt?token=abc

        ------------------- protobuf rpc definition --------------------

        // get download URL path and query for a file by path
        // to assemble complete URL: combine your gRPC server's scheme://host:port
        // with the returned downloadUrlPath example: if gRPC server is
        // https://api.example.com:8443 and result is
        // \"/static/{SCHEME}/{HOST}/{PREVIEW}/file.txt?token=abc\" then replace
        // {SCHEME} with \"https\", {HOST} with \"api.example.com:8443\", and {PREVIEW}
        // with \"true\" or \"false\" to get:
        // https://api.example.com:8443/static/https/api.example.com:8443/true/file.txt?token=abc
        rpc GetDownloadUrlPath(GetDownloadUrlPathRequest)
            returns (DownloadUrlPathInfo) {}

        ------------------- protobuf type definition -------------------

        message DownloadUrlPathInfo {
          string downloadUrlPath = 1; // path and query part of the download URL with placeholders (e.g.,
                                      // \"/static/{SCHEME}/{HOST}/{PREVIEW}/path/to/file.txt?token=abc123\")
          optional uint64 expiresIn = 2; // seconds until expiration, none means never expire
          optional string directUrl = 3; // direct URL for download, if available, this will override downloadUrlPath
          optional string userAgent = 4; // user agent to be used when accessing directUrl
          map<string, string> additionalHeaders = 5; // additional headers to be used when accessing directUrl
        }
        message GetDownloadUrlPathRequest {
          string path = 1;
          bool preview = 2;
          bool lazy_read = 3;
          bool get_direct_url = 4; // if true, get direct URL of cloud storage if available
        }
        """
        arg = to_message(clouddrive.pb2.GetDownloadUrlPathRequest, arg)
        if async_:
            return self.async_stub.GetDownloadUrlPath(arg, metadata=self.metadata)
        else:
            return self.stub.GetDownloadUrlPath(arg, metadata=self.metadata)

    @overload
    def StartRemoteUpload(
        self, 
        arg: dict | clouddrive.pb2.StartRemoteUploadRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.RemoteUploadStarted:
        ...
    @overload
    def StartRemoteUpload(
        self, 
        arg: dict | clouddrive.pb2.StartRemoteUploadRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.RemoteUploadStarted]:
        ...
    def StartRemoteUpload(
        self, 
        arg: dict | clouddrive.pb2.StartRemoteUploadRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.RemoteUploadStarted | Coroutine[Any, Any, clouddrive.pb2.RemoteUploadStarted]:
        """
        --- Remote Upload Protocol (grpc-web compatible) ---
        Start a remote upload session (unary, returns upload_id)

        ------------------- protobuf rpc definition --------------------

        // --- Remote Upload Protocol (grpc-web compatible) ---
        // Start a remote upload session (unary, returns upload_id)
        rpc StartRemoteUpload(StartRemoteUploadRequest)
            returns (RemoteUploadStarted) {}

        ------------------- protobuf type definition -------------------

        // Upload started reply
        message RemoteUploadStarted { string upload_id = 1; }
        // Start upload command
        message StartRemoteUploadRequest {
          string file_path = 1;
          uint64 file_size = 2;
          map<uint32, string> known_hashes = 3;
          // If true, client has local access to the original file and can compute
          // required hashes locally; server may rely on client-provided hashes and
          // request hash work over the channel instead of reading entire file
          bool client_can_calculate_hashes = 4;
        }
        """
        arg = to_message(clouddrive.pb2.StartRemoteUploadRequest, arg)
        if async_:
            return self.async_stub.StartRemoteUpload(arg, metadata=self.metadata)
        else:
            return self.stub.StartRemoteUpload(arg, metadata=self.metadata)

    @overload
    def RemoteUploadControl(
        self, 
        arg: dict | clouddrive.pb2.RemoteUploadControlRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def RemoteUploadControl(
        self, 
        arg: dict | clouddrive.pb2.RemoteUploadControlRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def RemoteUploadControl(
        self, 
        arg: dict | clouddrive.pb2.RemoteUploadControlRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        Control command for remote upload (unary). Returns empty on success; errors
        via status code.

        ------------------- protobuf rpc definition --------------------

        // Control command for remote upload (unary). Returns empty on success; errors
        // via status code.
        rpc RemoteUploadControl(RemoteUploadControlRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        // Control messages
        message PauseRemoteUpload {}
        // Control channel request from client to server
        message RemoteUploadControlRequest {
          string upload_id = 1; // Unique upload session ID
          oneof control {
            CancelRemoteUpload cancel = 2;
            PauseRemoteUpload pause = 3;
            ResumeRemoteUpload resume = 4;
          }
        }
        message ResumeRemoteUpload {}
        // Removed legacy RemoteHashDataUpload/Reply; clients must use
        // RemoteHashProgress for progress and final result
        """
        if async_:
            async def request():
                await self.async_stub.RemoteUploadControl(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.RemoteUploadControl(arg, metadata=self.metadata)
            return None

    @overload
    def RemoteUploadChannel(
        self, 
        arg: dict | clouddrive.pb2.RemoteUploadChannelRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> Iterable[clouddrive.pb2.RemoteUploadChannelReply]:
        ...
    @overload
    def RemoteUploadChannel(
        self, 
        arg: dict | clouddrive.pb2.RemoteUploadChannelRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, Iterable[clouddrive.pb2.RemoteUploadChannelReply]]:
        ...
    def RemoteUploadChannel(
        self, 
        arg: dict | clouddrive.pb2.RemoteUploadChannelRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> Iterable[clouddrive.pb2.RemoteUploadChannelReply] | Coroutine[Any, Any, Iterable[clouddrive.pb2.RemoteUploadChannelReply]]:
        """
        Server-side streaming channel for server requests (read/hash)

        ------------------- protobuf rpc definition --------------------

        // Server-side streaming channel for server requests (read/hash)
        rpc RemoteUploadChannel(RemoteUploadChannelRequest)
            returns (stream RemoteUploadChannelReply) {}

        ------------------- protobuf type definition -------------------

        // Hash data request (server asks client to compute hash locally and report via
        // RemoteHashProgress)
        message RemoteHashDataRequest {
          uint32 hash_type = 2;
          // Optional: when set and > 0 for MD5, client should return per-block MD5s
          // using this block size
          optional uint32 block_size = 3;
        }
        // Server-side streaming channel reply (server requests to client)
        message RemoteUploadChannelReply {
          string upload_id = 1;
          oneof request {
            RemoteReadDataRequest read_data = 2;
            RemoteHashDataRequest hash_data = 3;
            RemoteUploadStatusChanged status_changed = 4;
          }
        }
        message RemoteUploadChannelRequest { string device_id = 1; }
        // Remote upload status changed
        message RemoteUploadStatusChanged {
          UploadFileInfo.Status status = 1;
          string error_message = 2;
        }
        """
        arg = to_message(clouddrive.pb2.RemoteUploadChannelRequest, arg)
        if async_:
            return self.async_stub.RemoteUploadChannel(arg, metadata=self.metadata)
        else:
            return self.stub.RemoteUploadChannel(arg, metadata=self.metadata)

    @overload
    def RemoteReadData(
        self, 
        arg: dict | clouddrive.pb2.RemoteReadDataUpload, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.RemoteReadDataReply:
        ...
    @overload
    def RemoteReadData(
        self, 
        arg: dict | clouddrive.pb2.RemoteReadDataUpload, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.RemoteReadDataReply]:
        ...
    def RemoteReadData(
        self, 
        arg: dict | clouddrive.pb2.RemoteReadDataUpload, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.RemoteReadDataReply | Coroutine[Any, Any, clouddrive.pb2.RemoteReadDataReply]:
        """
        Client sends file data for remote read (unary)

        ------------------- protobuf rpc definition --------------------

        // Client sends file data for remote read (unary)
        rpc RemoteReadData(RemoteReadDataUpload) returns (RemoteReadDataReply) {}

        ------------------- protobuf type definition -------------------

        // Read data reply (server acks file data)
        message RemoteReadDataReply {
          bool success = 1;
          string error_message = 2;
          uint64 bytes_received = 3;
          bool is_last_chunk = 4;
        }
        message RemoteReadDataUpload {
          string upload_id = 1;
          uint64 offset = 3;
          uint64 length = 4;
          bool lazy_read = 5;
          bytes data = 6;
          bool is_last_chunk = 7;
        }
        """
        arg = to_message(clouddrive.pb2.RemoteReadDataUpload, arg)
        if async_:
            return self.async_stub.RemoteReadData(arg, metadata=self.metadata)
        else:
            return self.stub.RemoteReadData(arg, metadata=self.metadata)

    @overload
    def RemoteHashProgress(
        self, 
        arg: dict | clouddrive.pb2.RemoteHashProgressUpload, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.RemoteHashProgressReply:
        ...
    @overload
    def RemoteHashProgress(
        self, 
        arg: dict | clouddrive.pb2.RemoteHashProgressUpload, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.RemoteHashProgressReply]:
        ...
    def RemoteHashProgress(
        self, 
        arg: dict | clouddrive.pb2.RemoteHashProgressUpload, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.RemoteHashProgressReply | Coroutine[Any, Any, clouddrive.pb2.RemoteHashProgressReply]:
        """
        Client reports hash calculation progress (unary)

        ------------------- protobuf rpc definition --------------------

        // Client reports hash calculation progress (unary)
        rpc RemoteHashProgress(RemoteHashProgressUpload)
            returns (RemoteHashProgressReply) {}

        ------------------- protobuf type definition -------------------

        message RemoteHashProgressReply {}

        // File data and hash data are sent via separate unary RPCs below
        // Client-side hash calculation progress (e.g., when computing MD5/SHA1 locally)
        message RemoteHashProgressUpload {
          string upload_id = 1;
          // Bytes hashed so far and total bytes to hash (usually the file size)
          uint64 bytes_hashed = 2;
          uint64 total_bytes = 3;
          // Currently computing hash type (matches CloudDriveFile.HashType)
          CloudDriveFile.HashType hash_type = 4;
          // When present, indicates the final computed hash value for the given
          // hash_type
          optional string hash_value = 5;
          // Optional per-block hashes (lower-hex) for MD5 when requested via block_size
          repeated string block_hashes = 6;
        }
        """
        arg = to_message(clouddrive.pb2.RemoteHashProgressUpload, arg)
        if async_:
            return self.async_stub.RemoteHashProgress(arg, metadata=self.metadata)
        else:
            return self.stub.RemoteHashProgress(arg, metadata=self.metadata)

    @overload
    def GetWebServerConfig(
        self, 
        /, 
        async_: Literal[False] = False, 
    ) -> clouddrive.pb2.WebServerConfig:
        ...
    @overload
    def GetWebServerConfig(
        self, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, clouddrive.pb2.WebServerConfig]:
        ...
    def GetWebServerConfig(
        self, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> clouddrive.pb2.WebServerConfig | Coroutine[Any, Any, clouddrive.pb2.WebServerConfig]:
        """
        Web Server Configuration Management
        Get current web server configuration

        ------------------- protobuf rpc definition --------------------

        // Web Server Configuration Management
        // Get current web server configuration
        rpc GetWebServerConfig(google.protobuf.Empty) returns (WebServerConfig) {}

        ------------------- protobuf type definition -------------------

        // --- Web Server Configuration Messages ---
        message WebServerConfig {
          uint32 http_port = 1;
          uint32 https_port = 2;
          optional string cert_file = 3;
          optional string key_file = 4;
          bool enable_https = 5;
        }
        """
        if async_:
            return self.async_stub.GetWebServerConfig(Empty(), metadata=self.metadata)
        else:
            return self.stub.GetWebServerConfig(Empty(), metadata=self.metadata)

    @overload
    def SetWebServerConfig(
        self, 
        arg: dict | clouddrive.pb2.SetWebServerConfigRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def SetWebServerConfig(
        self, 
        arg: dict | clouddrive.pb2.SetWebServerConfigRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def SetWebServerConfig(
        self, 
        arg: dict | clouddrive.pb2.SetWebServerConfigRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        Set web server configuration and restart servers

        ------------------- protobuf rpc definition --------------------

        // Set web server configuration and restart servers
        rpc SetWebServerConfig(SetWebServerConfigRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message SetWebServerConfigRequest {
          optional uint32 http_port = 1;
          optional uint32 https_port = 2;
          optional string cert_file = 3;
          optional string key_file = 4;
          optional bool enable_https = 5;
          // Certificate content in PEM format - if provided, will be written to
          // certs/server.crt
          optional string cert_content = 6;
          // Private key content in PEM format - if provided, will be written to
          // certs/server.key
          optional string key_content = 7;
        }
        """
        if async_:
            async def request():
                await self.async_stub.SetWebServerConfig(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.SetWebServerConfig(arg, metadata=self.metadata)
            return None

    @overload
    def GenerateSelfSignedCert(
        self, 
        arg: dict | clouddrive.pb2.GenerateSelfSignedCertRequest, 
        /, 
        async_: Literal[False] = False, 
    ) -> None:
        ...
    @overload
    def GenerateSelfSignedCert(
        self, 
        arg: dict | clouddrive.pb2.GenerateSelfSignedCertRequest, 
        /, 
        async_: Literal[True], 
    ) -> Coroutine[Any, Any, None]:
        ...
    def GenerateSelfSignedCert(
        self, 
        arg: dict | clouddrive.pb2.GenerateSelfSignedCertRequest, 
        /, 
        async_: Literal[False, True] = False, 
    ) -> None | Coroutine[Any, Any, None]:
        """
        Generate self-signed certificate for HTTPS

        ------------------- protobuf rpc definition --------------------

        // Generate self-signed certificate for HTTPS
        rpc GenerateSelfSignedCert(GenerateSelfSignedCertRequest)
            returns (google.protobuf.Empty) {}

        ------------------- protobuf type definition -------------------

        message GenerateSelfSignedCertRequest {
          // If true, restart web servers after generating certificate and updating
          // config
          bool restart_servers = 1;
        }

        // ==================== 2FA Messages ====================
        """
        if async_:
            async def request():
                await self.async_stub.GenerateSelfSignedCert(arg, metadata=self.metadata)
                return None
            return request()
        else:
            self.stub.GenerateSelfSignedCert(arg, metadata=self.metadata)
            return None


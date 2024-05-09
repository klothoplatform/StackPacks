import * as pulumi from "@pulumi/pulumi"
import * as aws from "@pulumi/aws"
import * as fs from 'fs'
import * as path from 'path'
import * as which from 'which'
import * as mime from 'mime-types'

const kloConfig = new pulumi.Config("klo");

export function UploadStaticSite(bucket: aws.s3.Bucket, assets: {
  [key: string]: pulumi.asset.Asset | pulumi.asset.Archive;
}) {
  for (const [assetPath, asset] of Object.entries(assets)) {
    const objPath = path.relative("dist/", assetPath)
    const mimeType = mime.lookup(assetPath)
    new aws.s3.BucketObject(objPath, {
      bucket: bucket,
      source: asset,
      contentType: mimeType ? mimeType : undefined,
    }, {parent: bucket})
  }
}

export function UploadPulumiAccessToken(secret: aws.secretsmanager.Secret) {
  new aws.secretsmanager.SecretVersion('pulumi-access-token-secret', {
    secretId: secret.arn,
    secretString: kloConfig.requireSecret("PulumiAccessToken"),
  }, {parent: secret})
}

function findBinaryUpwards(bin: string): string | null {
  for (let dir = path.dirname(module.filename); dir != path.dirname("dir"); dir = path.dirname(dir)) {
    const binPath = path.join(dir, bin)
    if (fs.existsSync(binPath)) {
      return binPath
    }
  }
  return null
}

export function UploadBinaries(bucket: aws.s3.Bucket) {
  for (const bin of ["engine", "iac"]) {
    let binPath = which.sync(bin, {nothrow: true})
    if (!binPath) {
      binPath = findBinaryUpwards(bin)
    }
    if (binPath) {
      pulumi.log.info(`Uploading ${bin} binary from ${binPath}`)
      new aws.s3.BucketObject(bin, {
        bucket: bucket,
        source: new pulumi.asset.FileAsset(binPath),
      }, {parent: bucket})
      continue
    }
    pulumi.log.warn(`Could not find ${bin} binary in PATH or in the deploy directory`)
  }
}

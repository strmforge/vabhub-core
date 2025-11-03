Param(
  [string]$Org = $env:ORG
)
if (-not $Org) { $Org = "strmforge" }
$DefaultBranch = $env:DEFAULT_BRANCH
if (-not $DefaultBranch) { $DefaultBranch = "main" }

$repoName = Split-Path -Leaf (Get-Location)
$remote = "git@github.com:$Org/$repoName.git"

if (-not (Test-Path ".git")) {
  git init | Out-Null
  git checkout -b $DefaultBranch
}

if (-not (git config user.name)) {
  git config user.name ($env:GIT_USER_NAME ? $env:GIT_USER_NAME : $Org) | Out-Null
}
if (-not (git config user.email)) {
  $email = ($env:GIT_USER_EMAIL ? $env:GIT_USER_EMAIL : "noreply@users.noreply.github.com")
  git config user.email $email | Out-Null
}

git add -A
git commit -m ("chore({0}): bootstrap repo with templates" -f $repoName)
try { git remote remove origin | Out-Null } catch {}
git remote add origin $remote
git push -u origin $DefaultBranch
Write-Host "Pushed to $remote"

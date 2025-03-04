<#
.SYNOPSIS
    Master PowerShell script to launch multiple batches of Blender renders in parallel.

.DESCRIPTION
    For each batch, this script creates a subfolder (batchXX) under the output directory and launches Blender
    (via the generate-batch.py script) to render a batch of images. The script uses Start-Job to run multiple
    processes concurrently and throttles the number of parallel jobs using the --jobs parameter.

.PARAMETER num_batches
    The total number of batches to generate (default is 1).

.PARAMETER num_images_per_batch
    The number of images to render in each batch (default is 1).

.PARAMETER jobs
    The maximum number of parallel worker jobs (default is number of CPU cores + 4).

.PARAMETER model_path
    (Required) The path to the Blender model file.

.PARAMETER output_dir
    The directory where batch folders will be created (default is "batches" in the current directory).

.EXAMPLE
    pwsh ./generate_batches.ps1 -model_path "C:\path\to\model.glb" -num_batches 5 -num_images_per_batch 10 -jobs 8 -output_dir "C:\renders"
#>

param (
    [int]$num_batches = 1,
    [int]$num_images_per_batch = 1,
    [int]$jobs = ([Environment]::ProcessorCount + 4),
    [Parameter(Mandatory = $true)]
    [string]$model_path,
    [string]$output_dir = "batches"
)

function Show-Usage {
    Write-Host "Usage: ./generate_batches.ps1 -model_path <path> [-num_batches <number>] [-num_images_per_batch <number>] [-jobs <number>] [-output_dir <directory>]"
    exit 1
}

# Check that the required parameter is provided
if ([string]::IsNullOrEmpty($model_path)) {
    Write-Error "--model_path is required."
    Show-Usage
}

# Create the main output directory if it does not exist.
if (-not (Test-Path $output_dir)) {
    New-Item -ItemType Directory -Path $output_dir | Out-Null
}

# Array to store job objects.
$jobList = @()

# Loop over each batch.
for ($i = 1; $i -le $num_batches; $i++) {
    # Create a subfolder for the batch (e.g., batch01, batch02, etc.)
    $batchDir = Join-Path $output_dir (("batch{0:D2}" -f $i))
    if (-not (Test-Path $batchDir)) {
        New-Item -ItemType Directory -Path $batchDir | Out-Null
    }

    # Construct the Blender command.
    # Note: Adjust the path to your Blender executable if necessary.
    $cmd = "blender.exe --background --python $PSScriptRoot\generate-batch.py -- --model_path `"$model_path`" --num_images $num_images_per_batch --output_dir `"$batchDir`""
    Write-Host "Launching batch $i with command:"
    Write-Host $cmd

    # Start the job. The script block takes a command string and executes it.
    $job = Start-Job -ScriptBlock { param($cmdLine) Invoke-Expression $cmdLine } -ArgumentList $cmd
    $jobList += $job

    # Throttle the number of concurrently running jobs.
    while ((Get-Job -State Running).Count -ge $jobs) {
        Start-Sleep -Seconds 1
    }
}

# Wait for all jobs to complete.
Write-Host "Waiting for all batches to complete..."
Wait-Job -Job $jobList

# Optionally, display the output of each job.
foreach ($job in $jobList) {
    Receive-Job -Job $job | Write-Output
}

Write-Host "All batches completed. Results are stored in '$output_dir'."

#!/bin/csh -f

#SBATCH --output=OSSEtool_log.txt
#SBATCH --error=OSSEtool_err.txt
#SBATCH --account=s0818
#SBATCH --time=01:00:00
#SBATCH --nodes=1 --ntasks-per-node=40
#SBATCH --job-name=OSSEtool
#SBATCH --constraint="cas&cssro"
##SBATCH --constraint=sky
#SBATCH --qos=debug

umask 022
limit stacksize unlimited

source /usr/share/modules/init/csh
module load python/GEOSpyD/Min4.9.2_py3.9
python ./main.py

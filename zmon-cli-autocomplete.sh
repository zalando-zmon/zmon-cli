# bash completion for zmon
_zmon() {
    local cur prev opts base command

    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    command="${COMP_WORDS[0]}"

    _get_zmon_cmd() {
        local c=$1
        local p=$2
        echo $(for cmd in $(${c} ${p} --help | grep -A 10 ^Commands: | grep -v ^Commands: | awk '{ print $1 }'); do echo $cmd; done; )
    }

    # options that we can complete
    opts="--config-file -v --verbose -V --version -h --help alert-definitions check-definitions entities groups help members status"

    if [ $prev == $command ]; then
        if [[ ${cur} == [a-zA-Z]* ]] || [[ ${cur} == -* ]]; then
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
        fi
    fi

    case "${prev}" in
        alert-definitions|check-definitions|entities|groups|members)
            local cmd_defs=$(_get_zmon_cmd $command $prev)
            COMPREPLY=($(compgen -W "${cmd_defs}" -- ${cur})) 
            return 0
            ;;
        *)
            ;;
    esac
}

complete -F _zmon zmon

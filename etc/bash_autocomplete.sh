#!/bin/bash
_get_uid_list() {

    if [ -z $1 ]; then
        getent passwd | awk -F ':' '($NF !~ /nologin/) {print $1}' | grep -v course
    else
        p_uid=$( echo $1 | awk -F ',' '{print $NF}' )
        c_uid=$( echo $1 | sed "s/$p_uid//" )
        getent passwd | awk -F ':' '($NF !~ /nologin/) {print $1}' | grep -v course | grep $p_uid | sed -e "s/^/$c_uid/"
    fi
}

_get_pid_list() {

    prj_dir=/project

    if [ ! -z $1 ]; then
        prj_dir=$1
    fi

    ls --color=never $prj_dir
}

_prj_getacl() {

  # the completion word
  local cur=${COMP_WORDS[COMP_CWORD]}

  # the whole command-line 
  local line=${COMP_LINE}

  # Array variable storing the possible completions.
  COMPREPLY=()

  case "$cur" in
    -*)
        COMPREPLY=( $( compgen -W '-l -h --log --help --' -- $cur ) )
        ;;
    *)
        COMPREPLY=( $( compgen -W "$( _get_pid_list )" $cur ) )
        ;;
  esac

  return 0
}

_prj_setacl() {

  # the completion word
  local cur=${COMP_WORDS[COMP_CWORD]}

  # the whole command-line 
  local line=${COMP_LINE}

  # Array variable storing the possible completions.
  COMPREPLY=()

  case "$cur" in
    -*)
        COMPREPLY=( $( compgen -W '-a -c -u -l -h -f \
                               --admin --contributor --user --log --help --force --' -- $cur ) )
        ;;
    [0-9]*)
        COMPREPLY=( $( compgen -W "$( _get_pid_list )" $cur ) )
        ;;
    [a-z]*,)
        COMPREPLY=( $( compgen -W "$( _get_uid_list )" ) )
        ;;
    [a-z]*,[a-z]*)
        COMPREPLY=( $( compgen -W "$( _get_uid_list $cur )" -- $cur ) )
        ;;
    -a | --admin | -c | --contibutor | -u | --user | [a-z]* )
        COMPREPLY=( $( compgen -W "$( _get_uid_list )" $cur ) )
        ;;
    *)
        local pre_cur=${COMP_WORDS[COMP_CWORD-1]}

        case "$pre_cur" in
          -a | --admin | -c | --contibutor | -u | --user )
              COMPREPLY=( $( compgen -W "$( _get_uid_list )" $cur ) )
              ;;
        esac 
        ;;
  esac

  return 0
}

_prj_delacl() {

  # the completion word
  local cur=${COMP_WORDS[COMP_CWORD]}

  # the whole command-line 
  local line=${COMP_LINE}

  # Array variable storing the possible completions.
  COMPREPLY=()

  case "$cur" in
    -*)
        COMPREPLY=( $( compgen -W '-l -h -f \
                               --log --help --force --' -- $cur ) )
        ;;
    [0-9]*)
        COMPREPLY=( $( compgen -W "$( _get_pid_list )" $cur ) )
        ;;
    [a-z]*,)
        COMPREPLY=( $( compgen -W "$( _get_uid_list )" ) )
        ;;
    [a-z]*,[a-z]*)
        COMPREPLY=( $( compgen -W "$( _get_uid_list $cur )" -- $cur ) )
        ;;
    [a-z]*)
        COMPREPLY=( $( compgen -W "$( _get_uid_list )" $cur ) )
        ;;
  esac

  return 0
}

complete -F _prj_getacl prj_getacl
complete -F _prj_setacl prj_setacl
complete -F _prj_delacl prj_delacl

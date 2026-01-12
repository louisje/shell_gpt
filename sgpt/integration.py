bash_integration = """
# Shell-GPT integration BASH v0.2
[[ $- == *i* ]] && [[ -t 0 ]] && {
    stty -ixon  # Disable flow control to allow Ctrl-S
    _sgpt_bash() {
        if [[ -n "$READLINE_LINE" ]]; then
            READLINE_LINE=$(sgpt --shell <<< "$READLINE_LINE" --no-interaction)
            READLINE_POINT=${#READLINE_LINE}
        fi
    }
    bind -x '"\\C-s": _sgpt_bash'
}
# Shell-GPT integration BASH v0.2
"""

zsh_integration = """
# Shell-GPT integration ZSH v0.2
[[ $- == *i* ]] && [[ -t 0 ]] && {
    stty -ixon  # Disable flow control to allow Ctrl-S
    _sgpt_zsh() {
        if [[ -n "$BUFFER" ]]; then
            _sgpt_prev_cmd=$BUFFER
            BUFFER+="⌛"
            zle -I && zle redisplay
            BUFFER=$(sgpt --shell <<< "$_sgpt_prev_cmd" --no-interaction)
            zle end-of-line
        fi
    }
    zle -N _sgpt_zsh
    bindkey ^s _sgpt_zsh
}
# Shell-GPT integration ZSH v0.2
"""

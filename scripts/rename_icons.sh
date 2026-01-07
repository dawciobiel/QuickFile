#!/bin/bash
ICON_DIR="resources/icons/fonts.google.com"
declare -A NAME_MAP=(
    ["refresh_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="refresh.svg"
    ["arrow_upward_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="go_up.svg"
    ["description_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="view.svg"
    ["handyman_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="edit.svg"
    ["file_copy_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="copy.svg"
    ["move_item_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="move.svg"
    ["create_new_folder_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="new_folder.svg"
    ["scan_delete_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="delete.svg"
    ["search_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="search.svg"
    ["sync_alt_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="synchronize.svg"
    ["settings_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="settings.svg"
    ["rename_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="rename.svg"
    ["note_add_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="new_file.svg"
    ["person_edit_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="change_owner.svg"
    ["new_tab_right_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="new_tab.svg"
    ["close_tab_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="close_tab.svg"
    ["menage_favorites_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="manage_favorites.svg"
    ["bookmark_add_24dp_1F1F1F_FILL0_wght400_GRAD0_opsz24.svg"]="add_favorite.svg"
    ["properties.svg"]="file_properties.svg"
)
for old_name in "${!NAME_MAP[@]}"; do
    new_name=${NAME_MAP[$old_name]}
    if [ -f "$ICON_DIR/$old_name" ]; then
        git mv "$ICON_DIR/$old_name" "$ICON_DIR/$new_name"
        echo "Renamed $old_name to $new_name"
    fi
done

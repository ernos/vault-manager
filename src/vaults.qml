import QtQuick
import QtQuick.Controls
import QtQuick.Layouts


ApplicationWindow {
    id: window
    visible: true
    width: 1440
    height: 900
    minimumWidth: 1050
    minimumHeight: 650
    title: "Vault Manager"
    color: "#101418"

    property color panelColor: "#171d23"
    property color borderColor: "#303a44"
    property color textColor: "#f1f4f6"
    property color mutedTextColor: "#98a5af"
    property color accentColor: "#6aa9ff"
    property color successColor: "#4dcc8a"
    property color warningColor: "#e7b85c"
    property string currentTab: "Vaults"

    ListModel { id: vaultModel }

    function refresh() {
        vaultModel.clear()
        const list = vaultBackend.vaults()
        for (const v of list) vaultModel.append(v)
        refreshHistory()
    }

    function refreshHistory() {
        backupHistoryModel.clear()
        for (var i=0; i<vaultModel.count; ++i) {
            var v = vaultModel.get(i);
            for (var j=0; j<v.backups.length; ++j) {
                backupHistoryModel.append(v.backups[j]);
            }
        }
    }

    Component.onCompleted: {
        refresh()
    }
    Connections {
        target: vaultBackend
        function onVaultsChanged() { refresh() }
        function onOperationError(message) { errorDialog.text = message; errorDialog.open() }
        function onOperationMessage(message) { status.text = message }
        function onRequestSecret(name, recovery) {
            passDialog.vaultName = name
            passDialog.open()
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 230
            Layout.fillHeight: true
            color: "#13191e"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 10

                Label {
                    text: "Vault Manager"
                    color: window.textColor
                    font.pixelSize: 20
                    font.bold: true
                    Layout.bottomMargin: 24
                }

                Repeater {
                    model: ["Vaults", "Backups", "Activity", "Settings"]
                    delegate: Button {
                        required property string modelData
                        text: modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
                        onClicked: window.currentTab = modelData
                        background: Rectangle {
                            radius: 8
                            color: window.currentTab === modelData ? "#263b55" : "transparent"
                        }
                    }
                }

                Item { Layout.fillHeight: true }
                Label { text: "MVP"; color: "#697780" }
                Label { text: "Local vault protection"; color: "#697780" }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: 32
            spacing: 20

            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: window.currentTab; color: window.textColor; font.pixelSize: 28; font.bold: true }
                    Label {
                        text: window.currentTab === "Vaults" ? "Manage encrypted file-container vaults"
                             : window.currentTab === "Backups" ? "Review and manage vault backups"
                             : window.currentTab === "Activity" ? "View recent vault activity"
                             : "Configure Vault Manager"
                        color: window.mutedTextColor
                    }
                }
                Button {
                    text: "+ Create vault"
                    visible: window.currentTab === "Vaults"
                    onClicked: createDialog.open()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 10
                color: window.panelColor
                border.color: window.borderColor

                StackLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    currentIndex: ["Vaults","Backups","Activity","Settings"].indexOf(window.currentTab)

                    Item {
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 16

                            Rectangle {
                                Layout.fillWidth: true
                                implicitHeight: 72
                                radius: 9
                                color: "#2c281e"
                                border.color: "#66552f"
                                RowLayout {
                                    anchors.fill: parent
                                    anchors.margins: 16
                                    Label { text: "!"; color: window.warningColor; font.pixelSize: 24; font.bold: true }
                                    Label {
                                        Layout.fillWidth: true
                                        text: "Security limitation\nThe computer must be trusted while a vault is unlocked."
                                        color: "#d7c89f"
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }

                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 12
                                model: vaultModel
                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: 142
                                    radius: 10
                                    color: "#1b2229"
                                    border.color: window.borderColor
                                    ColumnLayout {
                                        anchors.fill: parent
                                        anchors.margins: 18
                                        RowLayout {
                                            Layout.fillWidth: true
                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                Label { text: model.name; color: window.textColor; font.pixelSize: 16; font.bold: true }
                                                Label {
                                                    text: model.mounted ? "● Mounted" : "● Locked"
                                                    color: model.mounted ? window.successColor : window.mutedTextColor
                                                }
                                            }
                                            Button {
                                                text: model.mounted ? "Lock" : "Unlock"
                                                onClicked: model.mounted
                                                    ? vaultBackend
                                                      .lockVault(model.name)
                                                    : vaultBackend.unlockVault(model.name)
                                            }
                                        }
                                        Rectangle { Layout.fillWidth: true; height: 1; color: window.borderColor }
                                        RowLayout {
                                            Label { text: "Size\n" + Math.round(model.size_bytes / 1048576) + " MiB"; color: window.mutedTextColor }
                                            Label { text: "Last backup\n" + (model.last_backup || "Never"); color: window.mutedTextColor; Layout.fillWidth: true }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    //Backups
                    Item {
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 16
                            Label { text: "Initiate Backup"; color: window.textColor; font.pixelSize: 22; font.bold: true }
                            ListView {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 120
                                spacing: 12
                                model: vaultModel
                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: 40
                                    radius: 6
                                    color: "#1b2229"
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        Label { text: model.name; color: window.textColor; Layout.fillWidth: true }
                                        Button { text: "Full"; onClicked: backupDestDialog.openBackup(model.name, "full") }
                                        Button { text: "Chunked"; onClicked: backupDestDialog.openBackup(model.name, "chunked") }
                                    }
                                }
                            }
                            Label { text: "Backup History"; color: window.textColor; font.pixelSize: 22; font.bold: true }
                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                spacing: 8
                                model: ListModel { id: backupHistoryModel }
                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: 50
                                    radius: 6
                                    color: "#1b2229"
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        Label { text: model.date; color: window.textColor }
                                        Label { text: model.type; color: window.mutedTextColor; Layout.fillWidth: true }
                                        Button { text: "Restore"; onClicked: vaultBackend.restoreRaw(model.path, "restore_target_path") }
                                        Button { text: "Delete"; onClicked: vaultBackend.deleteBackup(model.path) }
                                    }
                                }
                            }
                        }
                    }

                    // Backup Destination Dialog
                    Dialog {
                        id: backupDestDialog
                        property string vaultName
                        property string backupMode
                        title: "Choose Backup Destination"
                        modal: true
                        standardButtons: Dialog.Ok | Dialog.Cancel
                        contentItem: ColumnLayout {
                            TextField { id: destField; placeholderText: "/mnt/backup-drive/" }
                        }
                        function openBackup(name, mode) {
                            vaultName = name; backupMode = mode; open()
                        }
                        onAccepted: {
                            if (backupMode === "full") vaultBackend.startCompleteBackup(vaultName, destField.text)
                            else vaultBackend.startChunkedBackup(vaultName, destField.text, 64)
                            destField.clear()
                        }
                    }

                    // Restore Dialog
                    Dialog {
                        id: restoreDialog
                        title: "Restore Vault"
                        modal: true
                        standardButtons: Dialog.Ok | Dialog.Cancel
                        contentItem: ColumnLayout {
                            TextField { id: backupPath; placeholderText: "Backup file path" }
                            TextField { id: destPath; placeholderText: "Destination container path" }
                        }
                        onAccepted: {
                            vaultBackend.restoreRaw(backupPath.text, destPath.text)
                            backupPath.clear(); destPath.clear()
                        }
                    }

                    // Delete Backup Dialog
                    Dialog {
                        id: deleteBackupDialog
                        title: "Delete Backup"
                        modal: true
                        standardButtons: Dialog.Ok | Dialog.Cancel
                        contentItem: ColumnLayout {
                            TextField { id: deletePath; placeholderText: "Path to backup to delete" }
                        }
                        onAccepted: {
                            vaultBackend.deleteBackup(deletePath.text)
                            deletePath.clear()
                        }
                    }

                    //Activity
                    Item {
                        ColumnLayout {
                            anchors.fill: parent
                            spacing: 8
                            Label { text: "Activity Log"; color: window.textColor; font.pixelSize: 22; font.bold: true }

                            // Table Header
                            RowLayout {
                                Layout.fillWidth: true
                                Label { text: "Timestamp"; color: window.mutedTextColor; Layout.preferredWidth: 150 }
                                Label { text: "Message"; color: window.mutedTextColor; Layout.fillWidth: true }
                                Label { text: "Event"; color: window.mutedTextColor; Layout.preferredWidth: 100 }
                                Label { text: "Vault"; color: window.mutedTextColor; Layout.preferredWidth: 100 }
                            }

                            ListView {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                model: ListModel {
                                    id: activityModel
                                    // Roles: timestamp, message, event_type, associated_vault, severity
                                }
                                delegate: Rectangle {
                                    width: ListView.view.width
                                    height: 30
                                    color: index % 2 === 0 ? "#1b2229" : "#171d23"
                                    RowLayout {
                                        anchors.fill: parent
                                        anchors.margins: 4
                                        Label { text: model.timestamp || ""; color: window.textColor; Layout.preferredWidth: 150 }
                                        Label { text: model.message || ""; color: model.severity === "error" ? "red" : (model.severity === "warning" ? "yellow" : "green"); Layout.fillWidth: true }
                                        Label { text: model.event_type || ""; color: window.textColor; Layout.preferredWidth: 100 }
                                        Label { text: model.associated_vault || "-"; color: window.textColor; Layout.preferredWidth: 100 }
                                    }
                                }
                            }
                        }
                        Component.onCompleted: {
                            var logs = vaultBackend.activityLogs();
                            for (var i=0; i<logs.length; ++i) {
                                activityModel.append({
                                    timestamp: logs[i][0],
                                    message: logs[i][1],
                                    event_type: logs[i][2],
                                    associated_vault: logs[i][3],
                                    severity: logs[i][4]
                                });
                            }
                        }
                    }

                    //Settings
                    Item {
                        ColumnLayout {
                            anchors.fill: parent
                            Label { text: "Settings"; color: window.textColor; font.pixelSize: 22; font.bold: true }
                            Label {
                                text: "Linux/Kubuntu MVP. Automatic SFTP/cloud backups and compromised-OS protection are intentionally outside the MVP."
                                color: window.mutedTextColor
                                wrapMode: Text.WordWrap
                            }
                            Item { Layout.fillHeight: true }
                        }
                    }
                }
            }
            // Global Status Label
            Label { id: status; text: "Ready."; color: window.mutedTextColor }
        }
    }

    //Unlock Vault Dialog
    Dialog {
        id: passDialog
        property string vaultName
        title: "Unlock " + vaultName
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: TextField {
            id: passField
            echoMode: TextInput.Password
            placeholderText: "Passphrase"
        }
        onAccepted: {
            vaultBackend.unlockWithSecret(vaultName, passField.text, false)
            passField.clear()
        }
        onRejected: passField.clear()
    }

    //Create Vault Dialog box
    Dialog {
        id: createDialog
        title: "Create vault"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        contentItem: ColumnLayout {
            TextField { id: name; placeholderText: "Vault name" }
            TextField { id: container; placeholderText: "/home/peb/vault.img" }
            TextField { id: size; placeholderText: "Size MiB"; text: "4096" }
            TextField { id: pass; placeholderText: "Passphrase"; echoMode: TextInput.Password }
            CheckBox { id: makeRecovery; text: "Create recovery key"; checked: true }
        }
        onAccepted: vaultBackend.createVault(name.text, container.text, parseInt(size.text), pass.text, makeRecovery.checked)
    }

    //Error message
    Dialog {
        id: errorDialog
        property alias text: errorLabel.text
        title: "Operation failed"
        standardButtons: Dialog.Ok
        modal: true
        contentItem: Label { id: errorLabel; wrapMode: Text.WordWrap; width: 420 }
    }
}

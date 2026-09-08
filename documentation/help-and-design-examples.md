# Examples

## Status notification message

```qt

Example of a warning status notification warning message:

Rectangle {
    Layout.fillWidth: true
    Layout.preferredHeight: 72
    radius: 9
    color: "#2c281e"
    border.color: "#66552f"

    RowLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        Label {
            text: "!"
            color: window.warningColor
            font.pixelSize: 24
            font.bold: true
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3

            Label {
                text: "Security limitation"
                color: "#f5d68a"
                font.bold: true
            }

            Label {
                text: "The computer must be trusted while a vault is unlocked."
                color: "#cbbd99"
                font.pixelSize: 13
            }
        }

        Button {
            text: "Learn more"
        }
    }
}
```
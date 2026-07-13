package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// 7za-wrapper : appelle le vrai 7za.exe adjacent et masque l'exit code 2
// (warning "Cannot create symbolic link" sous Windows non-admin).
// winCodeSign-2.6.0.7z contient 2 symlinks macOS inutiles pour le packaging Win.
func main() {
	exe, err := os.Executable()
	if err != nil {
		fmt.Fprintln(os.Stderr, "wrapper: cannot resolve executable:", err)
		os.Exit(1)
	}
	real7za := filepath.Join(filepath.Dir(exe), "7za-real.exe")

	cmd := exec.Command(real7za, os.Args[1:]...)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	if err := cmd.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			code := exitErr.ExitCode()
			if code == 2 {
				// 7za retourne 2 pour "warning" (symlink creation failed).
				// Les fichiers utiles sont extraits ; on masque le code.
				if strings.Contains(os.Getenv("WRAPPER_DEBUG"), "1") {
					fmt.Fprintln(os.Stderr, "wrapper: masking 7za exit code 2")
				}
				os.Exit(0)
			}
			os.Exit(code)
		}
		fmt.Fprintln(os.Stderr, "wrapper: failed to run 7za:", err)
		os.Exit(1)
	}
	os.Exit(0)
}

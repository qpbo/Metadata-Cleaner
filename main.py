#!/usr/bin/env python3
"""
MetaScrub - Professional Image Metadata Cleaner
Author: Senior Python Developer
Purpose: Remove EXIF, GPS, camera info, and timestamps from images massively
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
from tqdm import tqdm
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class MetadataCleaner:
    """
    A robust class for removing metadata from images (EXIF, GPS, timestamps, camera info).
    
    This class handles batch processing of images in directories, creating clean copies
    without modifying the original files. It supports recursive directory traversal
    and provides detailed feedback about the cleaning process.
    """
    
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}
    
    def __init__(self, input_dir: str, output_dir: str, verbose: bool = False):
        """
        Initialize the MetadataCleaner with input and output directories.
        
        Args:
            input_dir: Path to the directory containing images to clean
            output_dir: Path to the directory where clean images will be saved
            verbose: If True, print detailed information during processing
        """
        self.input_path = Path(input_dir).resolve()
        self.output_path = Path(output_dir).resolve()
        self.verbose = verbose
        
        # Statistics tracking
        self.processed_count = 0
        self.error_count = 0
        self.errors: List[Tuple[str, str]] = []
        
        self._validate_paths()
    
    def _validate_paths(self) -> None:
        """
        Validate that the input directory exists and create the output directory if needed.
        
        Raises:
            FileNotFoundError: If the input directory doesn't exist
        """
        if not self.input_path.exists():
            raise FileNotFoundError(
                f"{Fore.RED}Input directory not found: {self.input_path}{Style.RESET_ALL}"
            )
        
        if not self.input_path.is_dir():
            raise NotADirectoryError(
                f"{Fore.RED}Input path is not a directory: {self.input_path}{Style.RESET_ALL}"
            )
        
        # Create output directory if it doesn't exist
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        if self.verbose:
            print(f"{Fore.CYAN}Input directory: {self.input_path}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}Output directory: {self.output_path}{Style.RESET_ALL}")
    
    def _find_images(self) -> List[Path]:
        """
        Recursively find all supported image files in the input directory.
        
        Returns:
            List of Path objects pointing to image files
        """
        images = []
        
        for ext in self.SUPPORTED_FORMATS:
            # Use rglob for recursive search (** pattern)
            images.extend(self.input_path.rglob(f'*{ext}'))
            images.extend(self.input_path.rglob(f'*{ext.upper()}'))
        
        return sorted(images)
    
    def _get_output_path(self, input_image: Path) -> Path:
        """
        Calculate the output path for a cleaned image, preserving directory structure.
        
        Args:
            input_image: Path to the input image file
            
        Returns:
            Path where the cleaned image should be saved
        """
        # Get the relative path from input_dir to the image
        relative_path = input_image.relative_to(self.input_path)
        
        # Construct the output path
        output_file = self.output_path / relative_path
        
        # Ensure the output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        return output_file
    
    def _clean_image_metadata(self, input_image: Path, output_image: Path) -> bool:
        """
        Remove all metadata from an image and save a clean copy.
        
        The key technique: Open the image and save it without the EXIF data segment.
        PIL's Image.save() only preserves EXIF if explicitly told to do so via the 
        'exif' parameter. By not passing it, we create a clean copy.
        
        Args:
            input_image: Path to the image to clean
            output_image: Path where the clean image should be saved
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Open the image
            with Image.open(input_image) as img:
                # Get the original format
                img_format = img.format
                
                # Create a new image without metadata
                # Key: We're loading the pixel data but NOT the EXIF data
                data = list(img.getdata())
                clean_img = Image.new(img.mode, img.size)
                clean_img.putdata(data)
                
                # Save without EXIF data
                # For JPEG, we explicitly avoid saving EXIF
                # For PNG/WEBP, we don't save metadata chunks
                save_kwargs = {
                    'format': img_format,
                    'quality': 95 if img_format in ['JPEG', 'WEBP'] else None,
                    'optimize': True
                }
                
                # Remove None values from kwargs
                save_kwargs = {k: v for k, v in save_kwargs.items() if v is not None}
                
                clean_img.save(output_image, **save_kwargs)
            
            return True
            
        except Exception as e:
            error_msg = f"Error processing {input_image.name}: {str(e)}"
            self.errors.append((str(input_image), str(e)))
            print(f"{Fore.RED}⚠️  {error_msg}{Style.RESET_ALL}")
            return False
    
    def process(self) -> None:
        """
        Main processing method: Find all images and clean their metadata.
        
        This method orchestrates the entire cleaning process, including:
        - Finding all images recursively
        - Processing each image with a progress bar
        - Collecting statistics and errors
        - Generating a final report
        """
        print(f"\n{Fore.YELLOW}🔍 Scanning for images...{Style.RESET_ALL}")
        images = self._find_images()
        
        if not images:
            print(f"{Fore.YELLOW}No images found in {self.input_path}{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}Found {len(images)} image(s) to process{Style.RESET_ALL}\n")
        
        # Process images with progress bar
        with tqdm(
            total=len(images),
            desc="🧹 Cleaning metadata",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            colour='green'
        ) as pbar:
            for img_path in images:
                output_path = self._get_output_path(img_path)
                
                if self.verbose:
                    tqdm.write(f"{Fore.CYAN}Processing: {img_path.name}{Style.RESET_ALL}")
                
                success = self._clean_image_metadata(img_path, output_path)
                
                if success:
                    self.processed_count += 1
                else:
                    self.error_count += 1
                
                pbar.update(1)
        
        self._print_report()
    
    def _print_report(self) -> None:
        """
        Print a final report with processing statistics and any errors encountered.
        """
        print(f"\n{'='*60}")
        print(f"{Fore.CYAN}📊 PROCESSING REPORT{Style.RESET_ALL}")
        print(f"{'='*60}")
        print(f"{Fore.GREEN}✅ Successfully processed: {self.processed_count}{Style.RESET_ALL}")
        print(f"{Fore.RED}❌ Errors encountered: {self.error_count}{Style.RESET_ALL}")
        
        if self.errors:
            print(f"\n{Fore.YELLOW}⚠️  Error Details:{Style.RESET_ALL}")
            for filepath, error in self.errors[:5]:  # Show first 5 errors
                print(f"  • {Path(filepath).name}: {error}")
            
            if len(self.errors) > 5:
                print(f"  ... and {len(self.errors) - 5} more errors")
        
        print(f"\n{Fore.CYAN}📁 Clean images saved to: {self.output_path}{Style.RESET_ALL}")
        print(f"{'='*60}\n")


def main() -> None:
    """
    Main entry point for the MetaScrub CLI application.
    
    Parses command-line arguments and initiates the metadata cleaning process.
    """
    parser = argparse.ArgumentParser(
        description='MetaScrub - Professional Image Metadata Cleaner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --input "./my_photos" --output "./clean_photos"
  python main.py --input "C:/Photos" --output "C:/Photos_Clean" --verbose
  
Supported formats: JPG, JPEG, PNG, WEBP

This tool removes:
  • EXIF data (camera settings, lens info, etc.)
  • GPS coordinates
  • Timestamps (creation date, modification date)
  • Camera make and model
  • Software information
  • Any other embedded metadata
        """
    )
    
    parser.add_argument(
        '--input',
        '-i',
        type=str,
        required=True,
        help='Input directory containing images to clean'
    )
    
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        required=True,
        help='Output directory for cleaned images (preserves folder structure)'
    )
    
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Enable verbose output (detailed processing information)'
    )
    
    args = parser.parse_args()
    
    try:
        # Create cleaner instance and process images
        cleaner = MetadataCleaner(
            input_dir=args.input,
            output_dir=args.output,
            verbose=args.verbose
        )
        
        cleaner.process()
        
    except Exception as e:
        print(f"\n{Fore.RED}❌ Fatal Error: {str(e)}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()
